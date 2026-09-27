import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet';
import { getLocationWeather, getWardBundle } from './api';
import { audienceTranslations } from './audienceTranslations';

const DEFAULT_LOCATION = 'Bhopal, Madhya Pradesh';
const riskLabels = {
  Green: { en: 'LOW HEAT RISK', hi: 'कम गर्मी जोखिम' },
  Yellow: { en: 'CAUTION', hi: 'सावधानी' },
  Orange: { en: 'HIGH HEAT RISK', hi: 'उच्च गर्मी जोखिम' },
  Red: { en: 'EXTREME HEAT RISK', hi: 'अत्यधिक गर्मी जोखिम' },
};

const safeValue = (value, suffix = '') => {
  if (value === undefined || value === null || value === '' || !Number.isFinite(Number(value))) return 'Not available';
  return `${value}${suffix}`;
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
  const [speaking, setSpeaking] = useState(false);
  const watchId = useRef(null);
  const lastCoordinates = useRef(null);
  const text = audienceTranslations[language];

  const profilePath = user?.role === 'government'
    ? '/government'
    : user?.user_type_selection === 'outdoor_worker'
      ? '/worker'
      : user?.user_type_selection === 'citizen'
        ? '/citizen'
        : '/select-role';

  useEffect(() => {
    try {
      localStorage.setItem('taap_language', language);
    } catch {
      // Ignore storage failures so the UI still renders.
    }
  }, [language]);

  useEffect(() => {
    getWardBundle('BPL_W003').then(setFallbackBundle).catch(() => {});
    return () => {
      if (watchId.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId.current);
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    };
  }, []);

  const fetchLocationWeather = (latitude, longitude, updating = false) => {
    lastCoordinates.current = { latitude, longitude };
    setLocationState(updating ? 'updating' : 'detected');
    setWeatherLoading(true);
    setWeatherError('');
    getLocationWeather(latitude, longitude)
      .then(setLocationData)
      .catch(() => setWeatherError(text.retry))
      .finally(() => setWeatherLoading(false));
  };

  const handlePosition = (position) => {
    const { latitude, longitude } = position.coords;
    const previous = lastCoordinates.current;
    const moved = !previous || Math.abs(previous.latitude - latitude) > 0.001 || Math.abs(previous.longitude - longitude) > 0.001;
    if (moved) fetchLocationWeather(latitude, longitude, Boolean(previous));
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
  const fallbackWeather = fallbackCurrent.weather || {};
  const current = locationData?.current || {
    temperature: fallbackWeather.temperature,
    feels_like: fallbackWeather.temperature,
    humidity: fallbackWeather.humidity,
    wind_speed: fallbackWeather.wind_speed,
    uv_index: fallbackWeather.uv_index,
    wbgt: fallbackCurrent.thermal_metrics?.wbgt,
    utci: fallbackCurrent.thermal_metrics?.utci,
    heat_index: fallbackCurrent.thermal_metrics?.heat_index,
  };
  const riskLevel = locationData?.risk?.level || fallbackCurrent.alert?.current_alert_level || 'Green';
  const advisory = locationData?.advisory || fallbackBundle?.recommendations?.citizen_guidance || {};
  const warningSigns = locationData?.advisory?.warning_signs || ['Dizziness', 'Unusual weakness', 'Headache', 'Nausea', 'Confusion', 'Fainting'];
  const coordinates = locationData?.location;
  const resources = locationData?.resources;
  const locationName = coordinates?.name || DEFAULT_LOCATION;
  const locationMessage = locationState === 'detecting' ? text.detecting : locationState === 'updating' ? text.updating : locationState === 'detected' ? text.detected : locationState === 'error' ? locationError : text.allowLocation;
  const riskLabel = riskLabels[riskLevel]?.[language] || riskLevel;

  return <div className="audience-dashboard">
    <header className="audience-header">
      <div className="audience-brand"><span className="audience-brand-icon">☀</span><div><span className="eyebrow">TAAP KAVACH</span><strong>{worker ? text.workerTitle : text.citizenTitle}</strong></div></div>
      <nav className="audience-actions" aria-label="Public navigation">
        <Link to="/" className="btn-sm">Home</Link>
        {user ? <Link to={profilePath} className="btn-sm btn-primary">Detailed Dashboard</Link> : null}
        {!user && <Link to="/login" className="btn-sm">Login</Link>}
        {!user && <Link to="/signup" className="btn-sm">Sign Up</Link>}
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
      <section className="location-panel"><div><span className="section-kicker">📍 {text.location}</span><h2>{locationName}</h2><p className={locationState === 'error' ? 'location-error' : ''}>{locationMessage}</p></div><button className="btn-sm btn-primary" onClick={detectLocation} disabled={locationState === 'detecting'}>📍 {locationState === 'detecting' ? text.detecting : text.detect}</button></section>
      {weatherError && <div className="audience-error"><span>{text.retry}</span><button className="btn-sm" onClick={refresh}>{text.refresh}</button></div>}
      <section className={`risk-card ${riskLevel}`}><div><span className="risk-icon">{riskLevel === 'Green' ? '🟢' : riskLevel === 'Yellow' ? '🟡' : riskLevel === 'Orange' ? '🟠' : '🔴'}</span><span className="risk-label">{riskLabel}</span><h2>{advisory.headline || 'Heat conditions'}</h2><p>{advisory.summary || 'Stay aware of heat conditions and take sensible precautions.'}</p></div><strong>{safeValue(locationData?.risk?.htsi || fallbackCurrent.thermal_metrics?.htsi, '/100')}</strong></section>
      <h2 className="audience-section-title">{text.current}</h2>
      {weatherLoading && <div className="audience-skeleton" aria-label={text.loading}><span /><span /><span /><span /></div>}
      <div className="conditions-grid"><Condition icon="🌡" label={text.temperature} value={safeValue(current.temperature, '°C')} /><Condition icon="🌡" label={text.feelsLike} value={safeValue(current.feels_like, '°C')} /><Condition icon="💧" label={text.humidity} value={safeValue(current.humidity, '%')} /><Condition icon="💨" label={text.wind} value={safeValue(current.wind_speed, ' km/h')} /><Condition icon="🔥" label={text.heatIndex} value={safeValue(current.heat_index, '°C')} /><Condition icon="☀️" label={text.uv} value={safeValue(current.uv_index)} /><Condition icon="🌡" label={text.wbgt} value={safeValue(current.wbgt, '°C')} /><Condition icon="🌡" label={text.utci} value={safeValue(current.utci, '°C')} /></div>
      <div className="audience-columns"><section className="audience-section"><h2>{worker ? text.advice : text.whatNow}</h2><p className="audience-guidance-headline">{advisory.headline}</p><p>{advisory.summary}</p>{worker && <div className="audience-reminders"><Reminder icon="💧" title={text.water} body="Drink water regularly, even before you feel thirsty." /><Reminder icon="🌳" title={text.shade} body="Take frequent breaks in shade or a cool, ventilated place." /><Reminder icon="☀️" title={text.peakHeat} body="Reduce strenuous outdoor work during peak afternoon heat." /></div>}<ul>{(advisory.steps || advisory.key_steps || []).map((step) => <li key={step}>{step}</li>)}</ul></section><section className="audience-section"><h2>{text.warningSigns}</h2><ul>{warningSigns.map((sign) => <li key={sign}>{sign}</li>)}</ul><p><strong>Call 108 or 112 for severe symptoms, confusion, or fainting.</strong></p></section></div>
      <section className="audience-section audience-map-section"><div className="section-heading"><h2>{text.location}</h2><span>{coordinates ? text.detected : text.allowLocation}</span></div>{coordinates ? <MapContainer key={`${coordinates.latitude}-${coordinates.longitude}`} center={[coordinates.latitude, coordinates.longitude]} zoom={13} scrollWheelZoom={false} className="audience-map"><TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><CircleMarker center={[coordinates.latitude, coordinates.longitude]} radius={10} pathOptions={{ color: '#b91c1c', fillColor: '#ef4444', fillOpacity: 0.9 }} /></MapContainer> : <div className="map-empty">{text.allowLocation}</div>}</section>
      <div className="audience-columns"><section className="audience-section"><h2>{text.help}</h2>{resources?.available && resources.items.length ? resources.items.map((item) => <div className="audience-help-row" key={item.id}><strong>{item.name}</strong><span>{item.type} · {item.distance_km} km</span></div>) : <p>{resources?.message || text.resourcesUnavailable}</p>}</section><section className="audience-section"><h2>{text.forecast}</h2>{fallbackBundle?.forecast?.slice(0, 4).map((day) => <div className="audience-help-row" key={day.date}><strong>{day.label}</strong><span className={`alert-badge ${day.alert_level}`}>{day.alert_level}</span><b>{safeValue(day.temperature, '°C')}</b></div>) || <p>{text.loading}</p>}</section></div>
    </main>
  </div>;
}

function Condition({ icon, label, value }) {
  return <div className="condition-card"><span>{icon}</span><small>{label}</small><strong>{value}</strong></div>;
}

function Reminder({ icon, title, body }) {
  return <div><strong>{icon} {title}</strong><span>{body}</span></div>;
}
