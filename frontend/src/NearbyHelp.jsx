import React, { useEffect, useMemo, useState } from 'react';
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet';
import './nearbyHelp.css';

/*
  Nearby Help & Emergency Services
  - Reuses `resources` already returned by getLocationWeather() (backend) when it has items.
  - Adds real facilities from OpenStreetMap (Overpass API, no API key needed).
  - Nothing is invented: if no facility is found, an empty-state message is shown.
*/

const OVERPASS_URLS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
];
const RADII = [5000, 10000];
const PAGE_SIZE = 8;

const COPY = {
  en: {
    title: 'Nearby Help & Emergency Services',
    subtitle: 'Hospitals, cooling shelters and drinking water close to your current location.',
    refresh: 'Search again',
    all: 'All',
    cats: { hospital: 'Hospitals', health: 'Health centres', emergency: 'Emergency', cooling: 'Cooling shelters', water: 'Drinking water' },
    types: {
      hospital: 'Hospital', health: 'Clinic / health centre', ambulance: 'Ambulance station', fire: 'Fire station',
      police: 'Police station', cooling: 'Cooling / relief shelter', water: 'Drinking water', waterPoint: 'Water point', other: 'Emergency service',
    },
    govt: 'Government',
    directions: 'Get Directions',
    call: 'Call',
    km: 'km',
    loading: 'Finding facilities near you…',
    empty: (r) => `No facilities were found within ${r} km of this location. Try searching again, or call 108 (ambulance) or 112 (emergency).`,
    error: 'Could not load nearby facilities right now. Please check your internet and search again.',
    showMore: 'Show more',
    source: 'Data: OpenStreetMap contributors and Taap Kavach records. Please call to confirm timings and availability.',
    you: 'You are here',
    mapLabel: 'Map of nearby facilities',
    noContact: 'Address not available',
    emergencyLine: 'Emergency: 108 (ambulance) · 112 (all emergencies)',
  },
  hi: {
    title: 'आस-पास मदद और आपातकालीन सेवाएँ',
    subtitle: 'आपकी मौजूदा लोकेशन के पास अस्पताल, कूलिंग शेल्टर और पीने के पानी की जगहें।',
    refresh: 'दोबारा खोजें',
    all: 'सभी',
    cats: { hospital: 'अस्पताल', health: 'स्वास्थ्य केंद्र', emergency: 'आपातकालीन सेवा', cooling: 'कूलिंग शेल्टर', water: 'पीने का पानी' },
    types: {
      hospital: 'अस्पताल', health: 'क्लिनिक / स्वास्थ्य केंद्र', ambulance: 'एम्बुलेंस स्टेशन', fire: 'फ़ायर स्टेशन',
      police: 'पुलिस थाना', cooling: 'कूलिंग / राहत शेल्टर', water: 'पीने का पानी', waterPoint: 'पानी की जगह', other: 'आपातकालीन सेवा',
    },
    govt: 'सरकारी',
    directions: 'रास्ता देखें',
    call: 'फ़ोन करें',
    km: 'किमी',
    loading: 'आपके पास की सुविधाएँ ढूँढ़ी जा रही हैं…',
    empty: (r) => `इस लोकेशन से ${r} किमी के अंदर कोई सुविधा नहीं मिली। दोबारा खोजें, या एम्बुलेंस के लिए 108 और किसी भी आपात स्थिति में 112 पर कॉल करें।`,
    error: 'अभी आस-पास की सुविधाओं की जानकारी नहीं मिल पा रही। इंटरनेट देख लें और फिर से खोजें।',
    showMore: 'और दिखाएँ',
    source: 'जानकारी: OpenStreetMap योगदानकर्ता और ताप कवच का रिकॉर्ड। जाने से पहले फ़ोन करके समय और उपलब्धता ज़रूर पूछ लें।',
    you: 'आप यहाँ हैं',
    mapLabel: 'आस-पास की सुविधाओं का नक्शा',
    noContact: 'पता उपलब्ध नहीं है',
    emergencyLine: 'आपातकाल: 108 (एम्बुलेंस) · 112 (हर तरह की आपात स्थिति)',
  },
};

const COLORS = { hospital: '#b91c1c', health: '#c2410c', emergency: '#1d4ed8', cooling: '#0f766e', water: '#0369a1', other: '#475569' };
const CATEGORY_ORDER = ['hospital', 'health', 'emergency', 'cooling', 'water'];

const toNumber = (v) => (v === null || v === undefined || v === '' ? NaN : Number(v));

const haversineKm = (lat1, lon1, lat2, lon2) => {
  const rad = (d) => (d * Math.PI) / 180;
  const a = Math.sin(rad(lat2 - lat1) / 2) ** 2
    + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lon2 - lon1) / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

// Keep only numbers that look like real phone numbers (7-13 digits).
const cleanPhone = (raw) => {
  if (!raw) return null;
  const first = String(raw).split(/[;,/]/)[0].trim();
  const digits = first.replace(/\D/g, '');
  if (digits.length < 7 || digits.length > 13) return null;
  return { display: first, dial: `${first.startsWith('+') ? '+' : ''}${digits}` };
};

const buildAddress = (tags) => {
  if (tags['addr:full']) return tags['addr:full'];
  const parts = [
    [tags['addr:housenumber'], tags['addr:street']].filter(Boolean).join(' '),
    tags['addr:suburb'] || tags['addr:neighbourhood'],
    tags['addr:city'] || tags['addr:town'] || tags['addr:village'],
    tags['addr:postcode'],
  ].filter(Boolean);
  return parts.length ? parts.join(', ') : null;
};

const classifyOsm = (tags) => {
  const a = tags.amenity;
  const h = tags.healthcare;
  const e = tags.emergency;
  if (a === 'hospital' || h === 'hospital') return { category: 'hospital', type: 'hospital' };
  if (e === 'cooling_centre' || a === 'cooling_centre' || tags.social_facility === 'shelter') return { category: 'cooling', type: 'cooling' };
  if (a === 'drinking_water' || e === 'drinking_water' || tags.man_made === 'water_tap') return { category: 'water', type: 'water' };
  if (a === 'water_point') return { category: 'water', type: 'waterPoint' };
  if (a === 'ambulance_station' || e === 'ambulance_station') return { category: 'emergency', type: 'ambulance' };
  if (a === 'fire_station') return { category: 'emergency', type: 'fire' };
  if (a === 'police') return { category: 'emergency', type: 'police' };
  if (a === 'clinic' || a === 'doctors' || h === 'centre' || h === 'clinic') return { category: 'health', type: 'health' };
  return null;
};

const isGovernment = (tags) => {
  const opType = (tags['operator:type'] || '').toLowerCase();
  if (opType === 'government' || opType === 'public') return true;
  return /govt|government|municipal|nagar nigam|district|civil hospital|aiims|phc|chc|primary health/i.test(
    `${tags.operator || ''} ${tags.name || ''}`,
  );
};

const buildQuery = (lat, lon, radius) => {
  const around = `(around:${radius},${lat},${lon})`;
  return `[out:json][timeout:20];(
    nwr${around}["amenity"~"^(hospital|clinic|doctors|drinking_water|water_point|cooling_centre|fire_station|police|ambulance_station)$"];
    nwr${around}["healthcare"~"^(hospital|centre|clinic)$"];
    nwr${around}["emergency"~"^(ambulance_station|cooling_centre|drinking_water)$"];
    nwr${around}["man_made"="water_tap"]["drinking_water"!="no"];
    nwr${around}["social_facility"="shelter"];
  );out center tags 250;`;
};

const fetchOverpass = async (lat, lon, radius, signal) => {
  let lastError;
  for (const url of OVERPASS_URLS) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `data=${encodeURIComponent(buildQuery(lat, lon, radius))}`,
        signal,
      });
      if (!res.ok) throw new Error(`Overpass ${res.status}`);
      const json = await res.json();
      return json.elements || [];
    } catch (err) {
      if (err.name === 'AbortError') throw err;
      lastError = err;
    }
  }
  throw lastError;
};

const fromOsm = (el, origin, t) => {
  const tags = el.tags || {};
  const cls = classifyOsm(tags);
  const latitude = toNumber(el.lat ?? el.center?.lat);
  const longitude = toNumber(el.lon ?? el.center?.lon);
  if (!cls || !Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  const phone = cleanPhone(tags.phone || tags['contact:phone'] || tags['contact:mobile']);
  return {
    id: `osm-${el.type}-${el.id}`,
    name: tags.name || tags['name:en'] || tags['name:hi'] || t.types[cls.type],
    category: cls.category,
    typeLabel: t.types[cls.type],
    government: isGovernment(tags),
    address: buildAddress(tags),
    phone,
    latitude,
    longitude,
    distance: haversineKm(origin.latitude, origin.longitude, latitude, longitude),
  };
};

// Items already returned by the existing backend `resources` object.
const fromBackend = (item, origin, t) => {
  const kind = String(item.type || item.category || '').toLowerCase();
  const category = /hospital/.test(kind) ? 'hospital'
    : /clinic|health|phc|chc|dispensary/.test(kind) ? 'health'
      : /shelter|cool|relief/.test(kind) ? 'cooling'
        : /water/.test(kind) ? 'water'
          : /ambulance|fire|police|emergency/.test(kind) ? 'emergency' : 'other';
  const latitude = toNumber(item.latitude ?? item.lat);
  const longitude = toNumber(item.longitude ?? item.lng ?? item.lon);
  const hasCoords = Number.isFinite(latitude) && Number.isFinite(longitude);
  const backendDistance = toNumber(item.distance_km);
  const distance = Number.isFinite(backendDistance)
    ? backendDistance
    : hasCoords ? haversineKm(origin.latitude, origin.longitude, latitude, longitude) : null;
  return {
    id: `api-${item.id ?? item.name}`,
    name: item.name || t.types.other,
    category,
    typeLabel: item.type || t.types.other,
    government: /govt|government|municipal|district|civil/i.test(`${item.operator || ''} ${item.ownership || ''} ${item.name || ''}`),
    address: item.address || null,
    phone: cleanPhone(item.phone || item.contact || item.contact_number),
    latitude: hasCoords ? latitude : null,
    longitude: hasCoords ? longitude : null,
    distance,
  };
};

const dedupe = (list) => {
  const seen = new Set();
  return list.filter((f) => {
    const key = `${f.name.toLowerCase()}|${f.latitude ? f.latitude.toFixed(3) : ''}|${f.longitude ? f.longitude.toFixed(3) : ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const directionsUrl = (f) => {
  const destination = f.latitude !== null ? `${f.latitude},${f.longitude}` : encodeURIComponent(`${f.name} ${f.address || ''}`.trim());
  return `https://www.google.com/maps/dir/?api=1&destination=${destination}&travelmode=driving`;
};

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [28, 28], maxZoom: 15 });
  }, [map, points]);
  return null;
}

export default function NearbyHelp({ location, resources, language = 'en', onRefresh }) {
  const t = COPY[language] || COPY.en;
  const latitude = toNumber(location?.latitude);
  const longitude = toNumber(location?.longitude);
  const hasLocation = Number.isFinite(latitude) && Number.isFinite(longitude);

  const [osmElements, setOsmElements] = useState([]);
  const [radiusUsed, setRadiusUsed] = useState(RADII[0]);
  const [status, setStatus] = useState('loading');
  const [reloadKey, setReloadKey] = useState(0);
  const [filter, setFilter] = useState('all');
  const [visible, setVisible] = useState(PAGE_SIZE);

  useEffect(() => {
    if (!hasLocation) return undefined;
    const controller = new AbortController();
    setStatus('loading');
    (async () => {
      try {
        let elements = [];
        let used = RADII[0];
        for (const radius of RADII) {
          used = radius;
          elements = await fetchOverpass(latitude, longitude, radius, controller.signal);
          if (elements.length) break;
        }
        setOsmElements(elements);
        setRadiusUsed(used);
        setStatus('done');
      } catch (err) {
        if (err.name !== 'AbortError') setStatus('error');
      }
    })();
    return () => controller.abort();
  }, [latitude, longitude, hasLocation, reloadKey]);

  const facilities = useMemo(() => {
    if (!hasLocation) return [];
    const origin = { latitude, longitude };
    const backend = resources?.available && Array.isArray(resources.items)
      ? resources.items.map((item) => fromBackend(item, origin, t)) : [];
    const osm = osmElements.map((el) => fromOsm(el, origin, t)).filter(Boolean);
    return dedupe([...backend, ...osm]).sort((a, b) => (a.distance ?? 999) - (b.distance ?? 999));
  }, [osmElements, resources, latitude, longitude, hasLocation, t]);

  const filtered = filter === 'all' ? facilities : facilities.filter((f) => f.category === filter);
  const shown = filtered.slice(0, visible);
  const mapPoints = [[latitude, longitude], ...shown.filter((f) => f.latitude !== null).map((f) => [f.latitude, f.longitude])];

  const refresh = () => {
    setVisible(PAGE_SIZE);
    setReloadKey((k) => k + 1);
    if (onRefresh) onRefresh();
  };

  return (
    <section className="audience-section nh-section" aria-labelledby="nh-title">
      <div className="nh-head">
        <div>
          <h2 id="nh-title">{t.title}</h2>
          <p className="nh-sub">{t.subtitle}</p>
        </div>
        <button type="button" className="btn-sm" onClick={refresh} disabled={status === 'loading'}>↻ {t.refresh}</button>
      </div>
      <p className="nh-emergency">{t.emergencyLine}</p>

      <div className="nh-filters" role="group" aria-label="Facility type">
        {['all', ...CATEGORY_ORDER].map((key) => (
          <button
            key={key}
            type="button"
            className={filter === key ? 'active' : ''}
            onClick={() => { setFilter(key); setVisible(PAGE_SIZE); }}
          >
            {key === 'all' ? t.all : t.cats[key]}
          </button>
        ))}
      </div>

      {hasLocation && (
        <div className="nh-map" role="region" aria-label={t.mapLabel}>
          <MapContainer key={`${latitude}-${longitude}`} center={[latitude, longitude]} zoom={13} scrollWheelZoom={false} className="nh-map-canvas">
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <FitBounds points={mapPoints} />
            <CircleMarker center={[latitude, longitude]} radius={9} pathOptions={{ color: '#1e3a8a', fillColor: '#2563eb', fillOpacity: 0.95 }}>
              <Tooltip>{t.you}</Tooltip>
            </CircleMarker>
            {shown.filter((f) => f.latitude !== null).map((f) => (
              <CircleMarker
                key={f.id}
                center={[f.latitude, f.longitude]}
                radius={7}
                pathOptions={{ color: '#fff', weight: 2, fillColor: COLORS[f.category] || COLORS.other, fillOpacity: 0.95 }}
              >
                <Tooltip>{f.name}</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      )}

      {status === 'loading' && !facilities.length && <p className="nh-state" role="status">{t.loading}</p>}
      {status === 'error' && !facilities.length && <p className="nh-state nh-error" role="alert">{t.error}</p>}
      {status === 'done' && !filtered.length && <p className="nh-state">{t.empty(radiusUsed / 1000)}</p>}

      <ul className="nh-list">
        {shown.map((f) => (
          <li key={f.id} className="nh-item">
            <span className="nh-dot" style={{ background: COLORS[f.category] || COLORS.other }} aria-hidden="true" />
            <div className="nh-info">
              <strong>{f.name}</strong>
              <span className="nh-meta">
                {f.typeLabel}
                {f.distance !== null ? ` · ${f.distance.toFixed(1)} ${t.km}` : ''}
                {f.government && <em className="nh-badge">{t.govt}</em>}
              </span>
              <span className="nh-address">{f.address || t.noContact}</span>
              {f.phone && <span className="nh-phone">{f.phone.display}</span>}
            </div>
            <div className="nh-actions">
              <a className="btn-sm btn-primary" href={directionsUrl(f)} target="_blank" rel="noopener noreferrer">{t.directions}</a>
              {f.phone && <a className="btn-sm" href={`tel:${f.phone.dial}`}>📞 {t.call}</a>}
            </div>
          </li>
        ))}
      </ul>

      {filtered.length > visible && (
        <button type="button" className="btn-sm nh-more" onClick={() => setVisible((v) => v + PAGE_SIZE)}>{t.showMore}</button>
      )}
      <p className="nh-source">{t.source}</p>
    </section>
  );
}
