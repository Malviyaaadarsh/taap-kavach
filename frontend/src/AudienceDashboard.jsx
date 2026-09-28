import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet';
import { getLocationWeather, getWardBundle, searchLocations } from './api';
import { audienceTranslations } from './audienceTranslations';
import taapKavachMark from './assets/taap-kavach-mark.svg';
import NearbyHelp from './NearbyHelp';

const DEFAULT_LOCATION = 'Bhopal, Madhya Pradesh';
const DEFAULT_COORDINATES = { latitude: 23.2599, longitude: 77.4126 };

const riskLabels = {
  Green: { en: 'LOW HEAT RISK', hi: 'गर्मी का खतरा कम' },
  Yellow: { en: 'CAUTION', hi: 'सावधान रहें' },
  Orange: { en: 'HIGH HEAT RISK', hi: 'गर्मी का खतरा ज़्यादा' },
  Red: { en: 'EXTREME HEAT RISK', hi: 'लू का बहुत गंभीर खतरा' },
};

// Labels that were hard-coded in English before. Hindi is written the way people actually speak.
const extraCopy = {
  en: {
    home: 'Home',
    login: 'Login',
    signUp: 'Sign Up',
    detailed: 'Detailed Dashboard',
    navLabel: 'Public navigation',
    notAvailable: 'Not available',
    heatConditions: 'Heat conditions',
    heatSummary: 'Stay aware of heat conditions and take sensible precautions.',
    warningSigns: ['Dizziness', 'Unusual weakness', 'Headache', 'Nausea', 'Confusion', 'Fainting'],
    waterBody: 'Drink water regularly, even before you feel thirsty.',
    shadeBody: 'Take frequent breaks in shade or a cool, ventilated place.',
    peakBody: 'Reduce strenuous outdoor work during peak afternoon heat.',
    callLine: 'Call 108 or 112 for severe symptoms, confusion, or fainting.',
  },
  hi: {
    home: 'होम',
    login: 'लॉगिन',
    signUp: 'साइन अप',
    detailed: 'विस्तृत डैशबोर्ड',
    navLabel: 'मुख्य नेविगेशन',
    notAvailable: 'उपलब्ध नहीं',
    heatConditions: 'गर्मी की स्थिति',
    heatSummary: 'गर्मी की स्थिति पर नज़र रखें और ज़रूरी सावधानी बरतें।',
    warningSigns: ['चक्कर आना', 'अजीब सी कमज़ोरी', 'सिरदर्द', 'जी मिचलाना', 'घबराहट या उलझन', 'बेहोशी'],
    waterBody: 'खूब पानी पिएँ, प्यास लगने का इंतज़ार न करें।',
    shadeBody: 'बीच-बीच में छाँव या ठंडी, हवादार जगह पर आराम करें।',
    peakBody: 'दोपहर की तेज़ धूप में भारी बाहरी काम करने से बचें।',
    callLine: 'गंभीर लक्षण, उलझन या बेहोशी हो तो तुरंत 108 या 112 पर कॉल करें।',
  },
};

const safeValue = (value, suffix = '', fallback = 'Not available') => {
  if (value === undefined || value === null || value === '' || !Number.isFinite(Number(value))) return fallback;
  return `${value}${suffix}`;
};

const formatObservedAt = (value, fallback = 'Not available') => {
  if (!value) return fallback;
  const observed = new Date(value);
  if (Number.isNaN(observed.getTime())) return fallback;
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(observed);
};

const readStoredLanguage = () => {
  try {
    return localStorage.getItem('taap_language') || 'en';
  } catch {
    return 'en';
  }
};

export default function AudienceDashboard({ worker = false, onLogout, user = null }) {
  const [language, setLanguage] = useState(readStoredLanguage);
  const [fallbackBundle, setFallbackBundle] = useState(null);
  const [locationData, setLocationData] = useState(null);
  const [locationState, setLocationState] = useState('idle');
  const [locationError, setLocationError] = useState('');
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const watchId = useRef(null);
  const lastCoordinates = useRef(null);
  const text = audienceTranslations[language];
  const extra = extraCopy[language] || extraCopy.en;
  const val = (value, suffix = '') => safeValue(value, suffix, extra.notAvailable);

  const profilePath = user?.role === 'government'
    ? '/government'
    : user?.user_type_selection === 'outdoor_worker'
      ? '/worker'
      : user?.user_type_selection === 'citizen'
        ? '/citizen'
        : '/select-role';

  // Logged-in users go to their existing detailed dashboard; guests are asked to log in first.
  const detailedPath = user ? profilePath : '/login';

  useEffect(() => {
    try {
      localStorage.setItem('taap_language', language);
    } catch {
      // Ignore storage failures so the UI still renders.
    }
  }, [language]);

  useEffect(() => {
    getWardBundle('BPL_W003').then(setFallbackBundle).catch(() => {});
    fetchLocationWeather(DEFAULT_COORDINATES.latitude, DEFAULT_COORDINATES.longitude, false, true, DEFAULT_LOCATION);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(handlePosition, (error) => {
        if (!lastCoordinates.current) {
          setLocationState('fallback');
          setLocationError(error.code === error.PERMISSION_DENIED ? text.denied : text.unavailable);
        }
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
      watchId.current = navigator.geolocation.watchPosition(handlePosition, () => {}, { enableHighAccuracy: false, maximumAge: 300000, timeout: 15000 });
    }
    return () => {
      if (watchId.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId.current);
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    };
  }, []);

  const fetchLocationWeather = (latitude, longitude, updating = false, clearCurrent = false, locationLabel = '') => {
    lastCoordinates.current = { latitude, longitude };
    setLocationState(updating ? 'updating' : 'detected');
    setWeatherLoading(true);
    setWeatherError('');
    if (clearCurrent) setLocationData(null);
    getLocationWeather(latitude, longitude)
      .then((data) => setLocationData({
        ...data,
        location: { ...data.location, name: locationLabel || data.location?.name },
      }))
      .catch(() => setWeatherError(text.retry))
      .finally(() => setWeatherLoading(false));
  };

  const handlePosition = (position) => {
    const { latitude, longitude } = position.coords;
    const previous = lastCoordinates.current;
    const moved = !previous || Math.abs(previous.latitude - latitude) > 0.001 || Math.abs(previous.longitude - longitude) > 0.001;
    if (moved) fetchLocationWeather(latitude, longitude, Boolean(previous), Boolean(previous));
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setLocationState('error');
      setLocationError(text.unsupported);
      return;
    }
    setLocationState('detecting');
    setLocationError('');
    navigator.geolocation.getCurrentPosition(
      handlePosition,
      (error) => {
        setLocationState('error');
        setLocationError(error.code === error.PERMISSION_DENIED ? text.denied : text.unavailable);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = navigator.geolocation.watchPosition(handlePosition, () => {}, { enableHighAccuracy: false, maximumAge: 300000, timeout: 15000 });
  };

  const submitLocationSearch = (event) => {
    event.preventDefault();
    const query = searchQuery.trim();
    if (query.length < 2) return;
    setSearchLoading(true);
    setWeatherError('');
    searchLocations(query)
      .then(setSearchResults)
      .catch(() => setWeatherError(text.retry))
      .finally(() => setSearchLoading(false));
  };

  const selectSearchedLocation = (result) => {
    if (watchId.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId.current);
    setSearchResults([]);
    setSearchQuery(result.city || result.name.split(',')[0]);
    fetchLocationWeather(result.latitude, result.longitude, false, true, result.name);
  };

  const speak = () => {
    if (!('speechSynthesis' in window)) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const advisory = locationData?.advisory || fallbackBundle?.recommendations?.citizen_guidance;
    const message = [advisory?.headline, advisory?.summary, ...(advisory?.steps || advisory?.key_steps || [])].filter(Boolean).join('. ');
    const utterance = new SpeechSynthesisUtterance(message || text.retry);
    utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const refresh = () => {
    if (lastCoordinates.current) fetchLocationWeather(lastCoordinates.current.latitude, lastCoordinates.current.longitude);
    else detectLocation();
  };

  const fallbackCurrent = fallbackBundle?.current || {};
  const current = locationData?.current || {};
  const riskLevel = locationData?.risk?.level || fallbackCurrent.alert?.current_alert_level || 'Green';
  const advisory = locationData?.advisory || fallbackBundle?.recommendations?.citizen_guidance || {};
  const warningSigns = locationData?.advisory?.warning_signs || extra.warningSigns;
  const coordinates = locationData?.location;
  const resources = locationData?.resources;
  const forecast = fallbackBundle?.forecast || [];
  const locationName = coordinates?.name || DEFAULT_LOCATION;
  const locationMessage = locationState === 'detecting' ? text.detecting : locationState === 'updating' ? text.updating : locationState === 'detected' ? text.detected : locationState === 'fallback' ? text.defaultLocation : locationState === 'error' ? locationError : text.allowLocation;
  const riskLabel = riskLabels[riskLevel]?.[language] || riskLevel;

  return <div className="audience-dashboard">
    <header className="audience-header">
      <div className="audience-brand"><img className="audience-brand-icon" src={taapKavachMark} alt="Taap Kavach" /><div><span className="eyebrow">TAAP KAVACH</span><strong>{worker ? text.workerTitle : text.citizenTitle}</strong></div></div>
      <nav className="audience-actions" aria-label={extra.navLabel}>
        <Link to="/" className="btn-sm">{extra.home}</Link>
        <Link to={detailedPath} className="btn-sm btn-primary nav-detailed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="3" width="7" height="9" />
            <rect x="14" y="3" width="7" height="5" />
            <rect x="14" y="12" width="7" height="9" />
            <rect x="3" y="16" width="7" height="5" />
          </svg>
          {extra.detailed}
        </Link>
        {!user && <Link to="/login" className="btn-sm">{extra.login}</Link>}
        {!user && <Link to="/signup" className="btn-sm">{extra.signUp}</Link>}
        {user ? <button className="btn-sm" onClick={onLogout}>{text.signOut}</button> : null}
        <div className="language-pair">
          <button className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>English</button>
          <span>|</span>
          <button className={language === 'hi' ? 'active' : ''} onClick={() => setLanguage('hi')}>हिंदी</button>
        </div>
      </nav>
    </header>
    <main className="audience-main">
      <div className="audience-welcome"><div><h1>{worker ? text.workerTitle : text.citizenTitle}</h1><p>{worker ? text.workerIntro : text.citizenIntro}</p></div><div className="audience-action-buttons"><button className="btn-sm btn-primary" onClick={speak}>{speaking ? `⏹ ${text.stop}` : `🔊 ${text.listen}`}</button><button className="btn-sm" onClick={refresh}>↻ {text.refresh}</button></div></div>
      <section className="location-panel"><div className="location-panel-content"><span className="section-kicker">📍 {text.location}</span><h2>{locationName}</h2><p className={locationState === 'error' ? 'location-error' : ''}>{locationMessage}</p>{locationData?.current && <p className="location-weather-meta">{current.condition} · {text.lastUpdated}: {formatObservedAt(current.observed_at, extra.notAvailable)}</p>}<form className="location-search" onSubmit={submitLocationSearch}><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder={text.searchLocation} aria-label={text.searchLocation} /><button className="btn-sm" type="submit" disabled={searchLoading}>{searchLoading ? text.searching : text.search}</button></form>{searchResults.length > 0 && <div className="location-search-results" aria-label={text.chooseLocation}>{searchResults.map((result) => <button type="button" key={`${result.latitude}-${result.longitude}`} onClick={() => selectSearchedLocation(result)}>{result.name}</button>)}</div>}</div><button className="btn-sm btn-primary location-detect-button" onClick={detectLocation} disabled={locationState === 'detecting'}>📍 {locationState === 'detecting' ? text.detecting : text.detect}</button></section>
      {weatherError && <div className="audience-error"><span>{text.retry}</span><button className="btn-sm" onClick={refresh}>{text.refresh}</button></div>}
      <section className={`risk-card ${riskLevel}`}><div><span className="risk-icon">{riskLevel === 'Green' ? '🟢' : riskLevel === 'Yellow' ? '🟡' : riskLevel === 'Orange' ? '🟠' : '🔴'}</span><span className="risk-label">{riskLabel}</span><h2>{advisory.headline || extra.heatConditions}</h2><p>{advisory.summary || extra.heatSummary}</p></div><strong>{val(locationData?.risk?.htsi, '/100')}</strong></section>
      <h2 className="audience-section-title">{text.current}</h2>
      {weatherLoading && <div className="audience-skeleton" aria-label={text.loading}><span /><span /><span /><span /></div>}
      <div className="conditions-grid"><Condition icon="🌡" label={text.temperature} value={val(current.temperature, '°C')} /><Condition icon="🌡" label={text.feelsLike} value={val(current.feels_like, '°C')} /><Condition icon="💧" label={text.humidity} value={val(current.humidity, '%')} /><Condition icon="💨" label={text.wind} value={val(current.wind_speed, ' km/h')} /><Condition icon="🔥" label={text.heatIndex} value={val(current.heat_index, '°C')} /><Condition icon="☀️" label={text.uv} value={val(current.uv_index)} /><Condition icon="🌡" label={text.wbgt} value={val(current.wbgt, '°C')} /><Condition icon="🌡" label={text.utci} value={val(current.utci, '°C')} /></div>
      <div className="audience-columns"><section className="audience-section"><h2>{worker ? text.advice : text.whatNow}</h2><p className="audience-guidance-headline">{advisory.headline}</p><p>{advisory.summary}</p>{worker && <div className="audience-reminders"><Reminder icon="💧" title={text.water} body={extra.waterBody} /><Reminder icon="🌳" title={text.shade} body={extra.shadeBody} /><Reminder icon="☀️" title={text.peakHeat} body={extra.peakBody} /></div>}<ul>{(advisory.steps || advisory.key_steps || []).map((step) => <li key={step}>{step}</li>)}</ul></section><section className="audience-section"><h2>{text.warningSigns}</h2><ul>{warningSigns.map((sign) => <li key={sign}>{sign}</li>)}</ul><p><strong>{extra.callLine}</strong></p></section></div>
      <section className="audience-section audience-map-section"><div className="section-heading"><h2>{text.location}</h2><span>{coordinates ? text.detected : text.allowLocation}</span></div>{coordinates ? <MapContainer key={`${coordinates.latitude}-${coordinates.longitude}`} center={[coordinates.latitude, coordinates.longitude]} zoom={13} scrollWheelZoom={false} className="audience-map"><TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><CircleMarker center={[coordinates.latitude, coordinates.longitude]} radius={10} pathOptions={{ color: '#b91c1c', fillColor: '#ef4444', fillOpacity: 0.9 }} /></MapContainer> : <div className="map-empty">{text.allowLocation}</div>}</section>

      <NearbyHelp location={coordinates} resources={resources} language={language} onRefresh={refresh} />

      <section className="audience-section"><h2>{text.forecast}</h2>{forecast.slice(0, 4).map((day) => <div className="audience-help-row" key={day.date}><strong>{day.label}</strong><span className={`alert-badge ${day.alert_level}`}>{day.alert_level}</span><b>{val(day.temperature_max ?? day.temperature, '°C')}</b></div>)}{forecast.length === 0 && <p>{text.loading}</p>}</section>
    </main>
  </div>;
}

function Condition({ icon, label, value }) {
  return <div className="condition-card"><span>{icon}</span><small>{label}</small><strong>{value}</strong></div>;
}

function Reminder({ icon, title, body }) {
  return <div><strong>{icon} {title}</strong><span>{body}</span></div>;
}
