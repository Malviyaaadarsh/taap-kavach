import React, { useEffect, useState, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Route, Routes, useNavigate, useLocation } from 'react-router-dom';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine, Legend } from 'recharts';
import 'leaflet/dist/leaflet.css';
import './styles.css';
import taapKavachMark from './assets/image.png';

import {
  getStates,
  getDistricts,
  getCities,
  getWards,
  getCitySummary,
  getCityRiskMap,
  getWardBundle,
  getAdminOverview,
  getAdminActions,
  getHealthcareOverview,
  getHealthcareReadiness,
  getMethodology,
  login as apiLogin,
  logout as apiLogout,
} from './api';

import { CHATBOT_PROMPTS, getChatbotReply } from './chatbot';

// Alert level configurations
const ALERT_CONFIG = {
  Green: { color: '#15803d', bg: '#f0fdf4', label: 'Normal / Routine Monitoring', desc: 'Normal thermal condition. General populace can continue standard routines.' },
  Yellow: { color: '#b45309', bg: '#fffbeb', label: 'Precautionary Advisory', desc: 'Precautionary heat advisory. Thermal discomfort noticeable during peak solar hours.' },
  Orange: { color: '#c2410c', bg: '#fff7ed', label: 'High Caution Alert', desc: 'High caution alert. Severe thermal stress risks heat exhaustion and rapid dehydration.' },
  Red: { color: '#b91c1c', bg: '#fef2f2', label: 'Severe Heat Emergency', desc: 'Severe heat emergency warning. Extreme physiological strain with high heat stroke risk.' },
};

// Map center controller
function MapViewUpdater({ center, zoom = 11 }) {
  const map = useMap();
  useEffect(() => {
    if (center && center.length === 2 && !isNaN(center[0])) {
      map.setView(center, zoom, { animate: true });
    }
  }, [center, zoom, map]);
  return null;
}

// Global Shell with sticky header & geographic hierarchy selector
function AppShell({
  children,
  user,
  onLogout,
  geo,
  onGeoChange,
  activeTab,
  onTabChange,
}) {
  return (
    <>
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Link to="/" className="brand" onClick={() => onTabChange('overview')}>
            <img className="brand-mark" src={taapKavachMark} alt="Taap Kavach" />
            <div className="brand-text">
              <b>TAAP KAVACH</b>
              <small>Human Thermal Stress Intelligence & Early Warning</small>
            </div>
          </Link>
          <span className="tier-badge">4th Tier: Ward/Zone</span>
        </div>

        <nav className="nav-tabs">
          <button className={`nav-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => onTabChange('overview')}>Overview</button>
          <button className={`nav-tab ${activeTab === 'map' ? 'active' : ''}`} onClick={() => onTabChange('map')}>Heat Map</button>
          <button className={`nav-tab ${activeTab === 'forecast' ? 'active' : ''}`} onClick={() => onTabChange('forecast')}>Ward Forecast</button>
          <button className={`nav-tab ${activeTab === 'risk' ? 'active' : ''}`} onClick={() => onTabChange('risk')}>Risk & Impact</button>
          <button className={`nav-tab ${activeTab === 'admin' ? 'active' : ''}`} onClick={() => onTabChange('admin')}>Administration</button>
          <button className={`nav-tab ${activeTab === 'healthcare' ? 'active' : ''}`} onClick={() => onTabChange('healthcare')}>Healthcare</button>
          <button className={`nav-tab ${activeTab === 'citizen' ? 'active' : ''}`} onClick={() => onTabChange('citizen')}>Citizen Advisory</button>
          <button className={`nav-tab ${activeTab === 'methodology' ? 'active' : ''}`} onClick={() => onTabChange('methodology')}>Methodology</button>
        </nav>

        <div className="topbar-right">
          {user ? (
            <div className="profile-chip">
              <span className="profile-avatar">{user.organization?.charAt(0) || 'U'}</span>
              <div className="profile-info">
                <b>{user.organization || 'Authorized User'}</b>
                <small>{user.user_type === 'local_administration' ? 'Municipal Admin' : 'Healthcare Facility'}</small>
              </div>
              <button className="btn-sm" onClick={onLogout} style={{ marginLeft: 6 }}>Sign Out</button>
            </div>
          ) : (
            <Link to="/login" className="btn-sm btn-primary">Portal Login</Link>
          )}
        </div>
      </header>

      {/* GEOGRAPHIC HIERARCHY SELECTOR TOOLBAR */}
      <section className="geo-toolbar">
        <div className="geo-selectors">
          <div className="geo-group">
            <label>State</label>
            <select value={geo.stateId} onChange={(e) => onGeoChange('state', e.target.value)}>
              {geo.states.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <span className="geo-divider">/</span>

          <div className="geo-group">
            <label>District</label>
            <select value={geo.districtId} onChange={(e) => onGeoChange('district', e.target.value)}>
              {geo.districts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {d.status === 'DEMONSTRATED' ? '(Prototype)' : '(Demo)'}
                </option>
              ))}
            </select>
          </div>
          <span className="geo-divider">/</span>

          <div className="geo-group">
            <label>City / Corporation</label>
            <select value={geo.cityId} onChange={(e) => onGeoChange('city', e.target.value)}>
              {geo.cities.map((c) => (
                <option key={c.id} value={c.id}>{c.short_name || c.name}</option>
              ))}
            </select>
          </div>
          <span className="geo-divider">/</span>

          <div className="geo-group">
            <label>Ward / Zone</label>
            <select value={geo.wardId} onChange={(e) => onGeoChange('ward', e.target.value)}>
              {geo.wards.map((w) => (
                <option key={w.ward_id} value={w.ward_id}>
                  {w.ward_name} ({w.zone} Zone)
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="geo-status-chip">
          {geo.districtId === 'bhopal' && geo.cityId === 'bhopal_bmc' ? (
            <>
              <span className="status-dot active"></span>
              <span style={{ color: '#166534', fontWeight: 600 }}>Bhopal: Fully Demonstrated Prototype</span>
            </>
          ) : (
            <>
              <span className="status-dot demo"></span>
              <span style={{ color: '#92400e', fontWeight: 600 }}>Demonstration Region (Integration Pending)</span>
            </>
          )}
          <span className="data-badge observed" style={{ marginLeft: 8 }}>14-18 Sep 2026 Snapshot</span>
        </div>
      </section>

      <main>{children}</main>

      <footer>
        Taap Kavach V2 SIH Prototype • Bhopal Municipal Corporation Heat Early Warning System • 
        Complements official IMD advisories; not an automated infrastructure controller or medical diagnostic tool.
      </footer>
    </>
  );
}

// ==========================================
// 1. OVERVIEW SCREEN (City-Wide Situation)
// ==========================================
function OverviewView({ citySummary, onSelectWard, onNavigateTab }) {
  if (!citySummary) return <div className="page-container"><div className="panel">Loading City Situation...</div></div>;

  const counts = citySummary.status_summary?.alert_counts || { Green: 0, Yellow: 2, Orange: 4, Red: 4 };
  const avg = citySummary.averages || {};
  const status = citySummary.status_summary || {};

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">MUNICIPAL HEAT ACTION OVERVIEW</span>
          <h1>{citySummary.city_name} — Current Heat Situation</h1>
          <p>City-wide thermal monitoring across all {status.total_monitored_wards} administrative zones.</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span className="data-badge observed">OBSERVED AGGREGATION</span>
          <div style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 4 }}>Updated: 18 Sep 2026 (15:30 IST)</div>
        </div>
      </div>

      {/* ALERT SUMMARY CARDS */}
      <div className="grid-4">
        <div className="panel" style={{ borderLeft: '5px solid var(--alert-red)', background: '#fff9f9' }}>
          <span className="eyebrow" style={{ color: 'var(--alert-red)' }}>RED EMERGENCY</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '6px 0', color: 'var(--alert-red)' }}>{counts.Red} Wards</strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Extreme stress. Work moratorium active.</span>
        </div>
        <div className="panel" style={{ borderLeft: '5px solid var(--alert-orange)', background: '#fffbf5' }}>
          <span className="eyebrow" style={{ color: 'var(--alert-orange)' }}>ORANGE HIGH CAUTION</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '6px 0', color: 'var(--alert-orange)' }}>{counts.Orange} Wards</strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>High caution for outdoor workers & elders.</span>
        </div>
        <div className="panel" style={{ borderLeft: '5px solid var(--alert-yellow)', background: '#fffdf5' }}>
          <span className="eyebrow" style={{ color: 'var(--alert-yellow)' }}>YELLOW PRECAUTION</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '6px 0', color: 'var(--alert-yellow)' }}>{counts.Yellow} Wards</strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Midday sun precaution recommended.</span>
        </div>
        <div className="panel" style={{ borderLeft: '5px solid var(--alert-green)', background: '#f8fdf9' }}>
          <span className="eyebrow" style={{ color: 'var(--alert-green)' }}>GREEN NORMAL</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '6px 0', color: 'var(--alert-green)' }}>{counts.Green} Wards</strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Baseline routine monitoring.</span>
        </div>
      </div>

      {/* CITY AVERAGES STATS GRID */}
      <div className="stats-grid">
        <div className="stat-cell">
          <span>City Avg Temp</span>
          <strong>{avg.temperature}<em>°C</em></strong>
        </div>
        <div className="stat-cell">
          <span>City Avg UTCI</span>
          <strong style={{ color: avg.utci >= 38 ? 'var(--alert-orange)' : 'var(--text-main)' }}>{avg.utci}<em>°C</em></strong>
        </div>
        <div className="stat-cell">
          <span>City Avg WBGT</span>
          <strong>{avg.wbgt}<em>°C</em></strong>
        </div>
        <div className="stat-cell">
          <span>Avg Heat Index</span>
          <strong>{avg.heat_index}<em>°C</em></strong>
        </div>
        <div className="stat-cell">
          <span>Taap Kavach HTSI</span>
          <strong style={{ color: 'var(--primary)' }}>{avg.htsi}<em>/100</em></strong>
        </div>
        <div className="stat-cell">
          <span>Total Exposed Pop</span>
          <strong>{(status.total_exposed_population / 1000).toFixed(0)}k<em>est.</em></strong>
        </div>
      </div>

      {/* HIGHEST RISK WARDS & CITY FORECAST TREND */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">PRIORITY INTERVENTION CORRIDORS</span>
              <h3>Highest-Risk Wards (Immediate Municipal Focus)</h3>
            </div>
            <button className="btn-sm" onClick={() => onNavigateTab('admin')}>View All Admin Actions</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Ward</th>
                <th>Alert</th>
                <th>HTSI</th>
                <th>UTCI</th>
                <th>Peak Forecast</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {citySummary.highest_risk_wards?.map((w) => (
                <tr key={w.ward_id} className="clickable" onClick={() => onSelectWard(w.ward_id)}>
                  <td><b>{w.ward_name}</b> <small style={{ color: 'var(--text-light)' }}>({w.zone})</small></td>
                  <td><span className={`alert-badge ${w.alert_level}`}>{w.alert_level}</span></td>
                  <td><b>{w.htsi}</b></td>
                  <td>{w.utci}°C</td>
                  <td>{w.peak_forecast_day} ({w.peak_forecast_alert})</td>
                  <td><button className="btn-sm btn-primary" style={{ padding: '3px 8px', fontSize: 10 }}>Inspect</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">CITY-WIDE 5-DAY EARLY WARNING</span>
              <h3>Forecast Severity Evolution</h3>
            </div>
            <span className="data-badge forecast">XGBoost + SARIMA Ensemble</span>
          </div>
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={citySummary.city_forecast_trend || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2ece8" />
              <XAxis dataKey="day" tickLine={false} axisLine={false} />
              <YAxis domain={['dataMin - 2', 'dataMax + 2']} tickLine={false} axisLine={false} />
              <Tooltip formatter={(val, name) => [`${val}°C`, name === 'city_avg_utci' ? 'Avg UTCI' : name]} />
              <ReferenceLine y={40} stroke="#b91c1c" strokeDasharray="3 3" label={{ value: 'Red (40°C)', fill: '#b91c1c', fontSize: 10 }} />
              <ReferenceLine y={38} stroke="#c2410c" strokeDasharray="3 3" label={{ value: 'Orange (38°C)', fill: '#c2410c', fontSize: 10 }} />
              <Line type="monotone" dataKey="city_avg_utci" name="City Avg UTCI" stroke="#0f5c53" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
            <span>Peak Heat Alert Projected on <b>Day +2 (20 Sep 2026)</b> with 6 Wards entering Red alert.</span>
            <button className="btn-sm" onClick={() => onNavigateTab('forecast')}>Inspect Ward Forecast</button>
          </div>
        </div>
      </div>

      {/* PRIORITY ACTIONS */}
      <div className="panel" style={{ marginTop: 18 }}>
        <div className="panel-header">
          <div>
            <span className="eyebrow">COORDINATED CITY ADVISORY</span>
            <h3>Top Recommended Municipal Heat Mitigation Actions</h3>
          </div>
          <button className="btn-sm btn-primary" onClick={() => onNavigateTab('admin')}>Open Heat Action Center</button>
        </div>
        <div className="grid-4" style={{ marginBottom: 0 }}>
          {citySummary.priority_municipal_actions?.map((act, i) => (
            <div key={i} style={{ background: 'var(--bg-surface-subtle)', padding: 12, border: '1px solid var(--border-color)', borderRadius: 3 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span className="eyebrow">{act.level} PRIORITY</span>
              </div>
              <b style={{ display: 'block', fontSize: 12, marginBottom: 4, color: 'var(--text-main)' }}>{act.title}</b>
              <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.35 }}>{act.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 2. HEAT MAP SCREEN
// ==========================================
function HeatMapView({ wards, selectedWardId, onSelectWard, onNavigateTab }) {
  const [filter, setFilter] = useState('ALL');
  const selectedWard = wards.find((w) => w.ward_id === selectedWardId) || wards[0];
  const centerPos = selectedWard ? [selectedWard.latitude, selectedWard.longitude] : [23.25, 77.43];

  const filteredWards = useMemo(() => {
    if (filter === 'RED') return wards.filter((w) => ['BPL_W002', 'BPL_W003', 'BPL_W006', 'BPL_W007', 'BPL_W009'].includes(w.ward_id));
    if (filter === 'ORANGE') return wards.filter((w) => ['BPL_W001', 'BPL_W004', 'BPL_W005', 'BPL_W008', 'BPL_W010'].includes(w.ward_id));
    if (filter === 'VULNERABLE') return wards.filter((w) => (w.outdoor_workers_percentage || 0) >= 28);
    return wards;
  }, [wards, filter]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">SPATIAL THERMAL RISK DISTRIBUTION</span>
          <h1>Bhopal Ward-Level Heat Risk GIS Map</h1>
          <p>Click any representative ward marker to view current thermal indices, peak early warning, and recommended actions.</p>
        </div>
        <div>
          <span className="data-badge derived">SPATIAL INTERPOLATION</span>
        </div>
      </div>

      <div className="map-filter-bar">
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-light)', marginRight: 6 }}>FILTERS:</span>
        <button className={`filter-chip ${filter === 'ALL' ? 'active' : ''}`} onClick={() => setFilter('ALL')}>All Monitored Wards (10)</button>
        <button className={`filter-chip ${filter === 'RED' ? 'active' : ''}`} onClick={() => setFilter('RED')}>Red Alert Wards</button>
        <button className={`filter-chip ${filter === 'ORANGE' ? 'active' : ''}`} onClick={() => setFilter('ORANGE')}>Orange Alert Wards</button>
        <button className={`filter-chip ${filter === 'VULNERABLE' ? 'active' : ''}`} onClick={() => setFilter('VULNERABLE')}>High Outdoor Worker Exposure (≥28%)</button>
      </div>

      <div className="map-container-wrap">
        <MapContainer center={[23.25, 77.43]} zoom={11} scrollWheelZoom={false}>
          <MapViewUpdater center={centerPos} zoom={12} />
          <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {filteredWards.map((ward) => {
            const isSelected = ward.ward_id === selectedWardId;
            const isRed = ['BPL_W002', 'BPL_W003', 'BPL_W006', 'BPL_W007', 'BPL_W009'].includes(ward.ward_id);
            const alertColor = isRed ? '#b91c1c' : '#c2410c';

            return (
              <CircleMarker
                key={ward.ward_id}
                center={[ward.latitude, ward.longitude]}
                radius={isSelected ? 14 : 9}
                pathOptions={{
                  color: isSelected ? '#18312b' : alertColor,
                  weight: isSelected ? 3 : 1.5,
                  fillColor: alertColor,
                  fillOpacity: isSelected ? 0.9 : 0.72,
                }}
              >
                <Popup>
                  <div style={{ minWidth: 200, padding: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <b style={{ fontSize: 14 }}>{ward.ward_name}</b>
                      <span className={`alert-badge ${isRed ? 'Red' : 'Orange'}`}>{isRed ? 'Red' : 'Orange'}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Zone: <b>{ward.zone}</b> · Density: <b>{ward.urban_density || 'High'}</b>
                    </div>
                    <div style={{ background: '#f5f8f6', padding: 6, borderRadius: 3, fontSize: 11, marginBottom: 8 }}>
                      <div>Population: <b>{ward.population?.toLocaleString()}</b></div>
                      <div>Outdoor Labor: <b>{ward.outdoor_workers_percentage}%</b></div>
                      <div>Peak Forecast Day: <b>Day +2 (Red)</b></div>
                    </div>
                    <button
                      className="btn-sm btn-primary"
                      style={{ width: '100%' }}
                      onClick={() => {
                        onSelectWard(ward.ward_id);
                        onNavigateTab('forecast');
                      }}
                    >
                      Open Ward Intelligence & Forecast
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 18, fontSize: 11 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><i style={{ width: 10, height: 10, background: '#b91c1c', display: 'inline-block' }} /> <b>Red</b>: UTCI ≥ 40°C (Critical)</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><i style={{ width: 10, height: 10, background: '#c2410c', display: 'inline-block' }} /> <b>Orange</b>: UTCI 38-40°C (High Caution)</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><i style={{ width: 10, height: 10, background: '#b45309', display: 'inline-block' }} /> <b>Yellow</b>: UTCI 35-38°C (Precaution)</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><i style={{ width: 10, height: 10, background: '#15803d', display: 'inline-block' }} /> <b>Green</b>: UTCI &lt; 35°C (Routine)</span>
        </div>
        <small style={{ color: 'var(--text-light)', fontSize: 10 }}>
          Representative ward centroid points for prototype demonstration. Official municipal polygon boundaries pending GIS shapefile release.
        </small>
      </div>
    </div>
  );
}

// ==========================================
// 3. WARD DASHBOARD & 4-DAY FORECAST SCREEN
// ==========================================
function WardForecastView({ bundle, onNavigateTab }) {
  const [metricKey, setMetricKey] = useState('utci');
  const [modelView, setModelView] = useState('ensemble');

  if (!bundle) return <div className="page-container"><div className="panel">Loading Ward Intelligence & Models...</div></div>;

  const current = bundle.current || {};
  const weather = current.weather || {};
  const thermal = current.thermal_metrics || {};
  const alert = current.alert || {};
  const htsiDetails = current.htsi_details || {};
  const riskDrivers = current.risk_drivers || { elevated_contributors: [], protective_contributors: [] };
  const history = bundle.history || [];
  const forecast = bundle.forecast || [];
  const forecastMeta = bundle.forecastMeta || {};
  const seasonal = bundle.seasonal || {};

  // Build continuous timeline: 10-day history + 4-day forecast
  const chartData = useMemo(() => {
    const list = [];
    history.forEach((h) => {
      list.push({
        date: h.date.slice(5),
        fullDate: h.date,
        day: h.is_today ? 'Today' : `D${h.day_index}`,
        utci: h.utci,
        wbgt: h.wbgt,
        heat_index: h.heat_index,
        temperature: h.temperature,
        htsi: h.htsi,
        phase: h.is_today ? 'TODAY' : 'OBSERVED',
        alert: h.alert_level,
      });
    });
    forecast.forEach((f) => {
      list.push({
        date: f.date.slice(5),
        fullDate: f.date,
        day: f.label,
        utci: modelView === 'xgboost' ? f.models.xgboost.utci : modelView === 'sarima' ? f.models.sarima.utci : f.utci,
        wbgt: modelView === 'xgboost' ? f.models.xgboost.wbgt : modelView === 'sarima' ? f.models.sarima.wbgt : f.wbgt,
        heat_index: f.heat_index,
        temperature: modelView === 'xgboost' ? f.models.xgboost.temperature : modelView === 'sarima' ? f.models.sarima.temperature : f.temperature,
        htsi: modelView === 'xgboost' ? f.models.xgboost.htsi : modelView === 'sarima' ? f.models.sarima.htsi : f.htsi,
        phase: 'FORECAST',
        alert: f.alert_level,
      });
    });
    return list;
  }, [history, forecast, modelView]);

  return (
    <div className="page-container">
      {/* ALERT BANNER */}
      <div className={`alert-banner ${alert.current_alert_level || 'Orange'}`}>
        <div>
          <span className={`alert-badge ${alert.current_alert_level}`}>{alert.current_alert_level} ALERT ACTIVE</span>
          <h2>{current.ward_name} ({current.zone} Zone) — {ALERT_CONFIG[alert.current_alert_level]?.label}</h2>
          <p>{alert.alert_message}</p>
          <div style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 6 }}>
            Elevation: <b>{current.demographics?.elevation_m}m</b> · Urban Density: <b>{current.demographics?.urban_density}</b> · Vegetation: <b>{current.demographics?.vegetation_coverage}</b>
          </div>
        </div>
        <div className="alert-action-box">
          <b>Recommended Immediate Action</b>
          <span>{alert.action_recommended}</span>
          <small>Valid from {alert.valid_from?.slice(0, 10)} through {alert.valid_until?.slice(0, 10)}</small>
        </div>
      </div>

      {/* METEOROLOGICAL OBSERVATION STATS */}
      <div className="stats-grid">
        <div className="stat-cell">
          <span>Air Temperature</span>
          <strong>{weather.temperature}<em>°C</em></strong>
        </div>
        <div className="stat-cell">
          <span>Relative Humidity</span>
          <strong>{weather.humidity}<em>%</em></strong>
        </div>
        <div className="stat-cell">
          <span>Wind Speed</span>
          <strong>{weather.wind_speed}<em>km/h</em></strong>
        </div>
        <div className="stat-cell">
          <span>Solar Irradiance</span>
          <strong>{weather.solar_radiation}<em>W/m²</em></strong>
        </div>
        <div className="stat-cell">
          <span>Atmospheric Pressure</span>
          <strong>{weather.atmospheric_pressure}<em>hPa</em></strong>
        </div>
        <div className="stat-cell">
          <span>UV Index</span>
          <strong>{weather.uv_index}<em>Index</em></strong>
        </div>
      </div>

      {/* THERMAL STRESS & HTSI COMPOSITE SCORE WITH CONTRIBUTORS */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">HUMAN THERMAL STRESS ENGINE</span>
              <h3>Taap Kavach HTSI — Prototype Composite Score</h3>
            </div>
            <span className="data-badge derived">PROTOTYPE COMPOSITE (0-100)</span>
          </div>

          <div className="htsi-score-box">
            <div className="htsi-large-val">
              {htsiDetails.score || 72}<span>/100</span>
            </div>
            <div>
              <span className={`htsi-category ${htsiDetails.risk_category || 'High'}`}>
                {htsiDetails.risk_category || 'High'} Thermal Stress
              </span>
              <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-muted)' }}>
                Deterministic composite combining physiological perceived heat, solar load, and moisture impedance.
              </p>
            </div>
          </div>

          <span className="eyebrow" style={{ display: 'block', marginBottom: 8 }}>Top Contributing Factors</span>
          <div className="contributor-list">
            {htsiDetails.top_contributors?.map((c, i) => (
              <div key={i} className="contributor-row">
                <span><b>{i + 1}.</b> {c.factor}</span>
                <div className="contributor-bar-bg">
                  <div className="contributor-bar-fill" style={{ width: `${Math.min(100, c.contribution_score * 3)}%` }} />
                </div>
                <span style={{ fontWeight: 600, textAlign: 'right' }}>{c.value}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 12, padding: '8px 10px', background: '#f5faf7', borderRadius: 3, fontSize: 11, display: 'flex', justifyContent: 'space-between' }}>
            <span>Convective Wind Mitigation Effect:</span>
            <b style={{ color: '#15803d' }}>-{htsiDetails.mitigating_factors?.[0]?.reduction_pts || 4.2} points ({weather.wind_speed} km/h)</b>
          </div>
        </div>

        {/* RISK DRIVERS PANEL (WHY IS RISK HIGH?) */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">DECISION EXPLAINABILITY</span>
              <h3>Why is Risk Elevated in {current.ward_name}?</h3>
            </div>
            <span className="data-badge observed">LOCAL MICROCLIMATE</span>
          </div>

          <div className="risk-drivers-container">
            <div className="driver-col elevated">
              <h4>Elevated Drivers (+)</h4>
              {riskDrivers.elevated_contributors?.map((d, i) => (
                <div key={i} className="driver-item">
                  <b>• {d.title}</b>
                  <span>{d.detail}</span>
                </div>
              ))}
            </div>

            <div className="driver-col protective">
              <h4>Protective Factors (-)</h4>
              {riskDrivers.protective_contributors?.map((d, i) => (
                <div key={i} className="driver-item">
                  <b>• {d.title}</b>
                  <span>{d.detail}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text-muted)', borderTop: '1px solid var(--border-light)', paddingTop: 8 }}>
            Combined physiological metrics: UTCI <b>{thermal.utci}°C</b> · WBGT <b>{thermal.wbgt}°C</b> · Heat Index <b>{thermal.heat_index}°C</b>.
          </div>
        </div>
      </div>

      {/* ALERT PROGRESSION TIMELINE */}
      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div>
            <span className="eyebrow">4-DAY EARLY WARNING TIMELINE</span>
            <h3>Alert Level Progression (Observed Today → 4 Days Forward)</h3>
          </div>
          <span className="data-badge forecast">PEAK: {forecastMeta.peak_forecast?.day_label}</span>
        </div>

        <div className="alert-timeline-wrap">
          {forecastMeta.alert_timeline?.map((step, i) => (
            <div key={i} className={`timeline-step ${step.is_peak ? 'peak peak-ribbon' : ''}`}>
              <span className="day-label">{step.day}</span>
              <span className="date-label">{step.date}</span>
              <span className={`timeline-badge alert-badge ${step.alert}`}>{step.alert}</span>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {forecastMeta.peak_forecast?.summary} Preemptive municipal interventions must be scheduled 48h prior to peak.
        </div>
      </div>

      {/* CONTINUOUS FORECAST CHART: PREVIOUS 10 DAYS -> NEXT 4 DAYS */}
      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div>
            <span className="eyebrow">TEMPORAL PROGRESSION (10 DAYS OBSERVED → NEXT 4 DAYS FORECAST)</span>
            <h3>Continuous Early Warning Timeline ({metricKey.toUpperCase()})</h3>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            {/* Metric Switcher */}
            <div style={{ display: 'flex', gap: 4 }}>
              {['utci', 'wbgt', 'heat_index', 'temperature', 'htsi'].map((k) => (
                <button
                  key={k}
                  className={`btn-sm ${metricKey === k ? 'btn-primary' : ''}`}
                  onClick={() => setMetricKey(k)}
                >
                  {k === 'heat_index' ? 'HI' : k.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Model Switcher */}
            <div style={{ display: 'flex', gap: 4 }}>
              <button className={`btn-sm ${modelView === 'ensemble' ? 'btn-primary' : ''}`} onClick={() => setModelView('ensemble')}>Ensemble</button>
              <button className={`btn-sm ${modelView === 'xgboost' ? 'btn-primary' : ''}`} onClick={() => setModelView('xgboost')}>XGBoost</button>
              <button className={`btn-sm ${modelView === 'sarima' ? 'btn-primary' : ''}`} onClick={() => setModelView('sarima')}>SARIMA</button>
            </div>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2ece8" />
            <XAxis dataKey="day" tickLine={false} axisLine={false} />
            <YAxis domain={['dataMin - 3', 'dataMax + 3']} tickLine={false} axisLine={false} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const dataPoint = payload[0].payload;
                  return (
                    <div style={{ background: '#fff', padding: '8px 12px', border: '1px solid #ccc', fontSize: 11, boxShadow: '0 2px 6px rgba(0,0,0,0.1)' }}>
                      <b>{dataPoint.fullDate} ({dataPoint.day})</b>
                      <div style={{ color: 'var(--text-light)', fontSize: 10 }}>Phase: {dataPoint.phase}</div>
                      <div style={{ marginTop: 4 }}>
                        {metricKey.toUpperCase()}: <b>{dataPoint[metricKey]} {metricKey === 'htsi' ? '/100' : '°C'}</b>
                      </div>
                      <div>Alert Level: <span className={`alert-badge ${dataPoint.alert}`} style={{ padding: '1px 5px', fontSize: 9 }}>{dataPoint.alert}</span></div>
                    </div>
                  );
                }
                return null;
              }}
            />
            {metricKey !== 'htsi' && (
              <>
                <ReferenceLine y={40} stroke="#b91c1c" strokeDasharray="3 3" label={{ value: 'Red (40°C)', fill: '#b91c1c', fontSize: 10 }} />
                <ReferenceLine y={38} stroke="#c2410c" strokeDasharray="3 3" label={{ value: 'Orange (38°C)', fill: '#c2410c', fontSize: 10 }} />
                <ReferenceLine y={35} stroke="#b45309" strokeDasharray="3 3" label={{ value: 'Yellow (35°C)', fill: '#b45309', fontSize: 10 }} />
              </>
            )}
            <ReferenceLine x="Today" stroke="#0a3f39" strokeWidth={2} strokeDasharray="4 4" label={{ value: 'NOW (Today)', fill: '#0a3f39', fontSize: 10, position: 'top' }} />
            <Line type="monotone" dataKey={metricKey} stroke="#0f5c53" strokeWidth={2.8} dot={{ r: 4 }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
          <span><b>Previous 10 Days:</b> Sep 09 to Sep 18 (Observed snapshot + baseline)</span>
          <span><b>Today:</b> Sep 18 (Current conditions)</span>
          <span><b>Next 4 Days:</b> Sep 19 to Sep 22 ({modelView.toUpperCase()} Early Warning)</span>
        </div>
      </div>

      {/* XGBOOST VS SARIMA COMPARISON TABLE */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">MODEL COMPARISON (4-DAY HORIZON)</span>
              <h3>XGBoost (Multivariate) vs sktime SARIMA (Temporal)</h3>
            </div>
            <span className="data-badge forecast">COMPLEMENTARY DUAL MODELS</span>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>Day</th>
                <th>Date</th>
                <th>XGBoost UTCI</th>
                <th>SARIMA UTCI</th>
                <th>Ensemble UTCI</th>
                <th>Alert</th>
              </tr>
            </thead>
            <tbody>
              {forecastMeta.model_comparison?.map((row, i) => (
                <tr key={i}>
                  <td><b>{row.label}</b></td>
                  <td>{row.date}</td>
                  <td>{row.XGBoost_UTCI}°C</td>
                  <td>{row.SARIMA_UTCI}°C</td>
                  <td><b>{row.Ensemble_UTCI}°C</b></td>
                  <td><span className={`alert-badge ${row.Alert}`}>{row.Alert}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <small style={{ display: 'block', marginTop: 10, color: 'var(--text-light)', fontSize: 10 }}>
            XGBoost accounts for non-linear multi-variable couplings (temp + humidity + radiation); SARIMA captures temporal autocorrelation and seasonal cyclic inertia.
          </small>
        </div>

        {/* MULTI-YEAR SEASONAL WINDOW COMPARISON */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">SEASONAL WINDOW ARCHITECTURE</span>
              <h3>Same Calendar Window Comparison (Sep 09 - Sep 18)</h3>
            </div>
            <span className="data-badge demo">MULTI-YEAR ALIGNMENT</span>
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            {seasonal['2026_current_window'] && (
              <div style={{ background: '#f5faf7', padding: 10, borderRadius: 3, borderLeft: '4px solid #0f5c53' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <b>2026 (Current Summer Window)</b>
                  <span className="data-badge observed">OBSERVED SNAPSHOT</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  10-Day Avg UTCI: <b>{seasonal['2026_current_window'].avg_utci}°C</b> · Avg HTSI: <b>{seasonal['2026_current_window'].avg_htsi}/100</b>
                </div>
              </div>
            )}
            {seasonal['2025_same_window'] && (
              <div style={{ background: '#fffdf5', padding: 10, borderRadius: 3, borderLeft: '4px solid #c28712' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <b>2025 (Same Calendar Window - Year -1)</b>
                  <span className="data-badge demo">DEMONSTRATION</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  10-Day Avg UTCI: <b>{seasonal['2025_same_window'].avg_utci}°C</b> · Avg HTSI: <b>{seasonal['2025_same_window'].avg_htsi}/100</b>
                </div>
              </div>
            )}
            {seasonal['2024_same_window'] && (
              <div style={{ background: '#fafafa', padding: 10, borderRadius: 3, borderLeft: '4px solid #82938e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <b>2024 (Same Calendar Window - Year -2)</b>
                  <span className="data-badge demo">DEMONSTRATION</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  10-Day Avg UTCI: <b>{seasonal['2024_same_window'].avg_utci}°C</b> · Avg HTSI: <b>{seasonal['2024_same_window'].avg_htsi}/100</b>
                </div>
              </div>
            )}
          </div>
          <small style={{ display: 'block', marginTop: 10, color: 'var(--text-light)', fontSize: 10 }}>
            Production concept evaluates inter-annual heat intensity across matched solar calendar windows. Historical baselines use structured demonstration series.
          </small>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 4. RISK & IMPACT SCREEN
// ==========================================
function RiskImpactView({ bundle, onNavigateTab }) {
  if (!bundle?.risk) return <div className="page-container"><div className="panel">Loading Risk & Demographic Impact...</div></div>;

  const risk = bundle.risk;
  const demo = risk.demographics || {};
  const plan = risk.planning_estimates || {};
  const healthRisk = risk.health_impact_risk || {};

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">DEMOGRAPHIC EXPOSURE & IMPACT ASSESSMENT</span>
          <h1>{risk.ward_name} — Population Vulnerability & Risk</h1>
          <p>Translating thermal stress into exposed human counts, municipal cooling demand, and healthcare surge estimates.</p>
        </div>
        <span className="data-badge derived">PLANNING ESTIMATES</span>
      </div>

      {/* HEALTH IMPACT RISK SCORE CARD */}
      <div className="panel" style={{ borderLeft: '6px solid #b91c1c', marginBottom: 20 }}>
        <div className="grid-2" style={{ alignItems: 'center', marginBottom: 0 }}>
          <div>
            <span className="eyebrow" style={{ color: '#b91c1c' }}>PROTOTYPE PLANNING ESTIMATE</span>
            <h2 style={{ margin: '4px 0', fontSize: 24 }}>Health Impact Risk: {healthRisk.level?.toUpperCase()} ({healthRisk.score}/100)</h2>
            <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 12 }}>{healthRisk.disclaimer}</p>
          </div>
          <div style={{ background: '#fff5f5', padding: 12, borderRadius: 4, border: '1px solid #fed7aa' }}>
            <span className="eyebrow">Key Risk Drivers</span>
            <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 11, color: 'var(--text-main)', lineHeight: 1.5 }}>
              {healthRisk.key_drivers?.map((drv, i) => <li key={i}>{drv}</li>)}
            </ul>
          </div>
        </div>
      </div>

      {/* POPULATION EXPOSURE MATRIX */}
      <div className="grid-3">
        <div className="panel">
          <span className="eyebrow">TOTAL WARD POPULATION</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '8px 0', color: 'var(--text-main)' }}>
            {demo.total_population?.toLocaleString()}
          </strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Registered residential census count</span>
        </div>
        <div className="panel" style={{ background: '#fff9f5', borderLeft: '4px solid #c2410c' }}>
          <span className="eyebrow" style={{ color: '#c2410c' }}>ESTIMATED POPULATION EXPOSED</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '8px 0', color: '#c2410c' }}>
            {plan.population_exposed?.toLocaleString()}
          </strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Under current {risk.alert_level} alert conditions</span>
        </div>
        <div className="panel" style={{ background: '#fff5f5', borderLeft: '4px solid #b91c1c' }}>
          <span className="eyebrow" style={{ color: '#b91c1c' }}>VULNERABLE POPULATION EXPOSED</span>
          <strong style={{ display: 'block', fontSize: 28, margin: '8px 0', color: '#b91c1c' }}>
            {plan.vulnerable_population_exposed?.toLocaleString()}
          </strong>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Senior citizens (60+) and young children</span>
        </div>
      </div>

      {/* PLANNING INDICATORS */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">DEMOGRAPHIC BREAKDOWN</span>
              <h3>High-Vulnerability Cohorts</h3>
            </div>
            <span className="data-badge observed">CENSUS MATRIX</span>
          </div>

          <table className="data-table">
            <tbody>
              <tr>
                <td><b>Elderly Citizens (Age 60+)</b></td>
                <td>{demo.elderly_percentage}% of ward</td>
                <td><b>{demo.elderly_population?.toLocaleString()}</b> persons</td>
              </tr>
              <tr>
                <td><b>Outdoor Manual Laborers & Vendors</b></td>
                <td>{demo.outdoor_worker_percentage}% of ward</td>
                <td><b>{demo.outdoor_worker_population?.toLocaleString()}</b> persons</td>
              </tr>
              <tr>
                <td><b>Children (Under Age 10)</b></td>
                <td>~14% planning estimate</td>
                <td><b>{demo.children_population_estimate?.toLocaleString()}</b> children</td>
              </tr>
              <tr>
                <td><b>Combined High-Vulnerability Total</b></td>
                <td>~35% of total ward</td>
                <td><b style={{ color: '#b91c1c' }}>{demo.total_vulnerable_population?.toLocaleString()}</b> persons</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">MUNICIPAL CIVIC DEMAND</span>
              <h3>Prototype Planning Indicators</h3>
            </div>
            <span className="data-badge derived">SIMULATED ESTIMATES</span>
          </div>

          <table className="data-table">
            <tbody>
              <tr>
                <td><b>Outdoor Labor Heat Exposure Count</b></td>
                <td><b>{plan.outdoor_worker_exposure?.toLocaleString()}</b> workers exposed</td>
              </tr>
              <tr>
                <td><b>Emergency Water Requirement</b></td>
                <td><b>{plan.estimated_water_requirement_litres_day?.toLocaleString()}</b> litres/day (Pyaaus + misting)</td>
              </tr>
              <tr>
                <td><b>Cooling Shelter Capacity</b></td>
                <td><b>{plan.cooling_centres_capacity}</b> public seats available</td>
              </tr>
              <tr>
                <td><b>Projected Heat Illness Patient Surge</b></td>
                <td><b style={{ color: '#c2410c' }}>+{plan.projected_heat_illness_patient_surge}</b> emergency cases est.</td>
              </tr>
              <tr>
                <td><b>Dedicated Hospital Heat Beds</b></td>
                <td><b>{plan.available_heat_beds}</b> beds ({plan.bed_readiness_percentage}% readiness)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 5. ADMINISTRATION WORKSPACE SCREEN
// ==========================================
function AdministrationView({ selectedWardId, onSelectWard }) {
  const [adminOverview, setAdminOverview] = useState(null);
  const [actionsData, setActionsData] = useState(null);

  useEffect(() => {
    getAdminOverview().then(setAdminOverview).catch(() => {});
    if (selectedWardId) {
      getAdminActions(selectedWardId).then(setActionsData).catch(() => {});
    }
  }, [selectedWardId]);

  if (!adminOverview || !actionsData) return <div className="page-container"><div className="panel">Loading Municipal Heat Action Center...</div></div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">MUNICIPAL DECISION SUPPORT</span>
          <h1>Municipal Heat Action Center — Operations Room</h1>
          <p>Targeted administrative interventions, priority ward dispatch, water distribution, and work-hour advisories.</p>
        </div>
        <span className="data-badge observed">EXECUTIVE VIEW</span>
      </div>

      {/* PRIORITY WARDS TABLE */}
      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div>
            <span className="eyebrow">SORTED BY HEAT HAZARD SEVERITY</span>
            <h3>Priority Wards Action Schedule (Bhopal Municipal Corporation)</h3>
          </div>
          <span className="data-badge forecast">CLICK ROW TO INSPECT WARD</span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Ward ID</th>
              <th>Ward Name</th>
              <th>Zone</th>
              <th>Alert</th>
              <th>HTSI Score</th>
              <th>UTCI</th>
              <th>Peak Day</th>
              <th>Vulnerable Pop</th>
              <th>Priority Municipal Action</th>
            </tr>
          </thead>
          <tbody>
            {adminOverview.priority_wards_table?.map((w) => (
              <tr
                key={w.ward_id}
                className="clickable"
                style={{ background: w.ward_id === selectedWardId ? '#f0fdf4' : 'transparent' }}
                onClick={() => onSelectWard(w.ward_id)}
              >
                <td><code>{w.ward_id}</code></td>
                <td><b>{w.ward_name}</b></td>
                <td>{w.zone}</td>
                <td><span className={`alert-badge ${w.alert_level}`}>{w.alert_level}</span></td>
                <td><b>{w.htsi}</b></td>
                <td>{w.utci}°C</td>
                <td>{w.peak_day}</td>
                <td>{w.vulnerable_population?.toLocaleString()}</td>
                <td><small>{w.priority_action}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* RECOMMENDED MUNICIPAL ACTIONS FOR SELECTED WARD */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">ACTION PROTOCOL FOR {actionsData.ward_name}</span>
              <h3>Concrete Municipal Response Directives</h3>
            </div>
            <span className={`alert-badge ${actionsData.alert_level}`}>{actionsData.alert_level}</span>
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            {actionsData.municipal_actions?.map((act, i) => (
              <div key={i} style={{ background: '#f8faf9', padding: 12, border: '1px solid var(--border-color)', borderRadius: 3 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <b style={{ color: 'var(--text-main)', fontSize: 13 }}>{act.action}</b>
                  <span className="eyebrow" style={{ color: act.priority === 'Critical' ? '#b91c1c' : '#c2410c' }}>{act.priority}</span>
                </div>
                <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)' }}>{act.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* COOLING CENTRES & SMS SIMULATION */}
        <div style={{ display: 'grid', gap: 18 }}>
          <div className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">PUBLIC COOLING HUBS</span>
                <h3>Designated Cooling Spaces in {actionsData.ward_name}</h3>
              </div>
              <span className="data-badge observed">ACTIVE / STANDBY</span>
            </div>

            {actionsData.cooling_centres?.map((cc) => (
              <div key={cc.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--border-light)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <b style={{ display: 'block', fontSize: 12 }}>{cc.name}</b>
                  <small style={{ color: 'var(--text-muted)' }}>{cc.address} · {cc.has_air_conditioning ? 'Air Conditioned' : 'Air Cooled'}</small>
                </div>
                <span className="btn-sm" style={{ background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', fontWeight: 600 }}>
                  {cc.capacity} seats ({cc.status})
                </span>
              </div>
            ))}
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">CIVIC WARNING BROADCAST</span>
                <h3>Automated SMS Alert Simulation</h3>
              </div>
              <span className="data-badge demo">SIMULATED READY</span>
            </div>

            <div style={{ background: '#f4f6f4', padding: 12, borderRadius: 3, border: '1px solid var(--border-color)', fontFamily: 'monospace', fontSize: 11 }}>
              {actionsData.simulated_sms_broadcast?.message}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 10, color: 'var(--text-light)' }}>
              <span>Target Audience: Registered contacts in {actionsData.ward_name}</span>
              <span>Estimated Reach: ~{actionsData.planning_estimates?.population_exposed?.toLocaleString()} recipients</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 6. HEALTHCARE WORKSPACE SCREEN
// ==========================================
function HealthcareView({ selectedWardId }) {
  const [readiness, setReadiness] = useState(null);
  const [checklist, setChecklist] = useState([]);

  useEffect(() => {
    if (selectedWardId) {
      getHealthcareReadiness(selectedWardId).then((data) => {
        setReadiness(data);
        setChecklist(data.readiness_checklist || []);
      }).catch(() => {});
    }
  }, [selectedWardId]);

  const toggleCheck = (id) => {
    setChecklist((items) =>
      items.map((it) => (it.id === id ? { ...it, checked: !it.checked } : it))
    );
  };

  if (!readiness) return <div className="page-container"><div className="panel">Loading Healthcare Facility Preparedness...</div></div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">HOSPITAL CAPACITY & EMERGENCY READINESS</span>
          <h1>Heat-Health Emergency Preparedness — {readiness.ward_name}</h1>
          <p>Monitoring bed capacity, patient load surges, cold immersion readiness, and electrolyte stocks.</p>
        </div>
        <span className={`alert-badge ${readiness.current_alert}`}>{readiness.current_alert} ALERT ACTIVE</span>
      </div>

      {/* METRIC STRIP */}
      <div className="stats-grid">
        <div className="stat-cell">
          <span>Projected Patient Surge</span>
          <strong style={{ color: '#c2410c' }}>+{readiness.patient_surge_planning_estimate}<em>cases est.</em></strong>
        </div>
        <div className="stat-cell">
          <span>Dedicated Heat Beds</span>
          <strong>{readiness.heat_beds_available}<em>beds</em></strong>
        </div>
        <div className="stat-cell">
          <span>Bed Readiness Score</span>
          <strong style={{ color: '#15803d' }}>{readiness.bed_readiness_percentage}<em>%</em></strong>
        </div>
        <div className="stat-cell">
          <span>Forecast Peak Day</span>
          <strong style={{ color: '#b91c1c' }}>{readiness.peak_forecast_day}</strong>
        </div>
        <div className="stat-cell">
          <span>Expected Severity</span>
          <strong>{readiness.expected_heat_stress_severity}</strong>
        </div>
        <div className="stat-cell">
          <span>Elderly Population (60+)</span>
          <strong>{readiness.demographics?.elderly_population?.toLocaleString()}</strong>
        </div>
      </div>

      {/* CHECKLIST & NEARBY HOSPITALS */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">FACILITY VERIFICATION</span>
              <h3>Heat Illness Preparedness Checklist</h3>
            </div>
            <span className="data-badge observed">CLINICAL OPERATIONAL CHECKLIST</span>
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            {checklist.map((item) => (
              <label key={item.id} className="checklist-item">
                <input
                  type="checkbox"
                  checked={item.checked !== false}
                  onChange={() => toggleCheck(item.id)}
                />
                <span style={{ color: item.checked !== false ? 'var(--text-main)' : 'var(--text-muted)' }}>
                  <b>{item.item}</b>
                </span>
              </label>
            ))}
          </div>

          <div style={{ marginTop: 14, background: '#f5faf7', padding: 10, borderRadius: 3, border: '1px solid #c2e5d5', fontSize: 11 }}>
            <b>Clinical Protocol Notice:</b> Ensure casualty triage teams deploy active evaporative misting and ice pack application to axillae/groin within 15 minutes of suspected heat stroke admission.
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">TERTIARY & SECONDARY CARE</span>
              <h3>Nearby Healthcare Facilities</h3>
            </div>
            <span className="data-badge observed">CAPACITY METRICS</span>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>Facility</th>
                <th>Distance</th>
                <th>Total Beds</th>
                <th>Heat Beds</th>
                <th>ORS / Saline Stock</th>
                <th>Readiness</th>
              </tr>
            </thead>
            <tbody>
              {readiness.healthcare_facilities?.map((h) => (
                <tr key={h.id}>
                  <td><b>{h.name}</b><br/><small style={{ color: 'var(--text-muted)' }}>{h.type}</small></td>
                  <td>{h.distance_km} km</td>
                  <td>{h.total_beds}</td>
                  <td><b style={{ color: '#b91c1c' }}>{h.heat_stroke_beds}</b></td>
                  <td>{h.ors_packet_stock} ORS / {h.saline_iv_stock} IV</td>
                  <td><span className="data-badge observed">{h.readiness_score}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 7. CITIZEN ADVISORY SCREEN
// ==========================================
function CitizenView({ bundle }) {
  if (!bundle?.recommendations) return <div className="page-container"><div className="panel">Loading Public Advisory...</div></div>;

  const current = bundle.current || {};
  const recs = bundle.recommendations || {};
  const guide = recs.citizen_guidance || {};
  const alert = current.alert || {};
  const weather = current.weather || {};

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">PUBLIC HEALTH GUIDANCE</span>
          <h1>Citizen Heat Advisory — {current.ward_name}</h1>
          <p>Actionable, simple, jargon-free health protection steps for you and your family.</p>
        </div>
        <span className={`alert-badge ${alert.current_alert_level}`}>{alert.current_alert_level} LEVEL</span>
      </div>

      {/* PROMINENT STATUS CARD */}
      <div className="panel" style={{ background: '#fff9f5', borderLeft: '6px solid var(--alert-orange)', marginBottom: 20 }}>
        <h2 style={{ fontSize: 24, margin: '4px 0', color: 'var(--text-main)' }}>{guide.headline}</h2>
        <p style={{ margin: '6px 0 12px', fontSize: 13, color: 'var(--text-muted)' }}>{guide.summary}</p>
        <div style={{ display: 'flex', gap: 20, fontSize: 12 }}>
          <span>Current Air Temp: <b>{weather.temperature}°C</b></span>
          <span>Relative Humidity: <b>{weather.humidity}%</b></span>
          <span>Perceived Heat Stress: <b>High</b></span>
        </div>
      </div>

      {/* 5-STEP ACTION GUIDE */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">ACTIONABLE DEFENSE</span>
              <h3>What Should You Do Today?</h3>
            </div>
          </div>
          <div style={{ display: 'grid', gap: 10 }}>
            {guide.key_steps?.map((step, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ background: '#0f5c53', color: '#fff', width: 22, height: 22, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 700, flexShrink: 0 }}>
                  {i + 1}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-main)', lineHeight: 1.4 }}>{step}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16, padding: 12, background: '#fef3c7', borderRadius: 3, fontSize: 11, color: '#92400e' }}>
            <b>Vulnerable Family Members:</b> {guide.vulnerable_guidance}
          </div>
        </div>

        {/* EMERGENCY HELPLINES & COOLING POINT */}
        <div style={{ display: 'grid', gap: 18 }}>
          <div className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">FREE PUBLIC SHELTER</span>
                <h3>Nearest Municipal Cooling Center</h3>
              </div>
            </div>
            {recs.cooling_centres?.[0] && (
              <div style={{ background: '#f5faf7', padding: 12, borderRadius: 3, border: '1px solid #c8e8db' }}>
                <b style={{ fontSize: 13, display: 'block' }}>{recs.cooling_centres[0].name}</b>
                <p style={{ margin: '4px 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>{recs.cooling_centres[0].address}</p>
                <div style={{ fontSize: 11 }}>
                  <span>Capacity: <b>{recs.cooling_centres[0].capacity} persons</b></span> · 
                  <span style={{ color: '#15803d', marginLeft: 6, fontWeight: 600 }}>Free Drinking Water & ORS Available</span>
                </div>
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">24/7 SUPPORT</span>
                <h3>Emergency Helplines</h3>
              </div>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {recs.emergency_contacts?.map((c, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-light)', fontSize: 12 }}>
                  <span>{c.service}</span>
                  <b style={{ color: '#0f5c53' }}>{c.number}</b>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 8. METHODOLOGY & TECHNICAL FRAMEWORK
// ==========================================
function MethodologyView() {
  const [method, setMethod] = useState(null);

  useEffect(() => {
    getMethodology().then(setMethod).catch(() => {});
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title-wrap">
          <span className="eyebrow">TECHNICAL SPECIFICATIONS & VALIDATION</span>
          <h1>Taap Kavach Scientific Framework & Methodology</h1>
          <p>The mathematical and computational architecture translating meteorological observations into human thermal stress.</p>
        </div>
        <span className="data-badge observed">SIH V2 SPECIFICATION</span>
      </div>

      <div className="grid-2">
        <div className="panel">
          <span className="eyebrow">FOUR-TIER EARLY WARNING PARADIGM</span>
          <h3 style={{ margin: '4px 0 12px' }}>Localized Fourth Tier Architecture</h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Traditional heatwave advisories operate across three tiers (National → Regional → District). 
            Taap Kavach introduces the crucial <b>Fourth Tier (Ward/Zone level)</b> that resolves urban heat islands, 
            vegetation disparities, and building density variations.
          </p>

          <table className="data-table" style={{ marginTop: 12 }}>
            <tbody>
              <tr><td><b>Tier 1: National</b></td><td>IMD synoptic scale weather forecasts</td></tr>
              <tr><td><b>Tier 2: Regional</b></td><td>State meteorological center bulletins</td></tr>
              <tr><td><b>Tier 3: District</b></td><td>District disaster management broad warnings</td></tr>
              <tr><td><b style={{ color: '#0f5c53' }}>Tier 4: Taap Kavach</b></td><td><b>Ward-level physiological thermal stress, HTSI, and municipal action triggers</b></td></tr>
            </tbody>
          </table>
        </div>

        <div className="panel">
          <span className="eyebrow">COMPOSITE FORMULATION</span>
          <h3 style={{ margin: '4px 0 12px' }}>Taap Kavach HTSI Composite Equation</h3>
          <div style={{ background: '#f5faf7', padding: 12, borderRadius: 3, border: '1px solid #c2e5d5', fontFamily: 'monospace', fontSize: 11 }}>
            HTSI = [0.35 * UTCI_norm + 0.25 * WBGT_norm + 0.20 * HI_norm + 0.12 * Solar_norm + 0.08 * Humidity_norm] - Wind_mitigation
          </div>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.4 }}>
            Normalized on a 0-100 scale: Low (&lt;40, Green), Moderate (41-60, Yellow), High (61-80, Orange), Extreme (81-100, Red). 
            Integrates ISO 7243 WBGT, Universal Thermal Climate Index (UTCI), Rothfusz Heat Index, and convective boundary layer ventilation.
          </p>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="panel-header">
          <div>
            <span className="eyebrow">AI/ML FORECASTING SUBSYSTEM</span>
            <h3>Complementary Machine Learning Architecture: XGBoost + sktime SARIMA</h3>
          </div>
        </div>
        <div className="grid-2" style={{ marginBottom: 0 }}>
          <div>
            <b>1. XGBoost Multivariate Regressor:</b>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Trained on meteorological features (ambient temp, humidity, wind, pressure, solar radiation, diurnal hour, and ward indices). 
              Learns non-linear environmental couplings and surface heat retention.
            </p>
          </div>
          <div>
            <b>2. sktime SARIMA Time-Series Forecaster:</b>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Captures temporal trend, multi-day cyclic inertia, and diurnal periodicity. 
              Provides a classical statistical anchor complementary to the tree-based XGBoost model.
            </p>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 20 }}>
        <span className="eyebrow">SCIENTIFIC INTEGRITY ROADMAP</span>
        <h3 style={{ margin: '4px 0 8px' }}>Model Validation & Production Roadmap</h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 12px' }}>
          Current V2 prototype operates on the supplied 5-day MET Norway Bhopal snapshot with ward offsets. 
          The production roadmap incorporates walk-forward temporal cross-validation across 3 years of summer archives:
        </p>
        <div className="grid-4" style={{ marginBottom: 0 }}>
          <div style={{ background: '#f8faf8', padding: 10, border: '1px solid var(--border-color)' }}>
            <span className="eyebrow">METRIC 1</span>
            <b style={{ display: 'block', fontSize: 12 }}>MAE & RMSE</b>
            <small style={{ color: 'var(--text-muted)' }}>Continuous error evaluation for predicted UTCI & WBGT (°C)</small>
          </div>
          <div style={{ background: '#f8faf8', padding: 10, border: '1px solid var(--border-color)' }}>
            <span className="eyebrow">METRIC 2</span>
            <b style={{ display: 'block', fontSize: 12 }}>Alert Precision</b>
            <small style={{ color: 'var(--text-muted)' }}>Classification precision for Orange/Red heatwave threshold breach</small>
          </div>
          <div style={{ background: '#f8faf8', padding: 10, border: '1px solid var(--border-color)' }}>
            <span className="eyebrow">METRIC 3</span>
            <b style={{ display: 'block', fontSize: 12 }}>False Alarm Rate</b>
            <small style={{ color: 'var(--text-muted)' }}>Minimizing public advisory fatigue and municipal economic disruption</small>
          </div>
          <div style={{ background: '#f8faf8', padding: 10, border: '1px solid var(--border-color)' }}>
            <span className="eyebrow">METRIC 4</span>
            <b style={{ display: 'block', fontSize: 12 }}>Missed-Event Rate</b>
            <small style={{ color: 'var(--text-muted)' }}>Critical safety metric ensuring no extreme heatwave days pass unalerted</small>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 9. LOGIN PAGE
// ==========================================
function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('admin.bhopal@taapkavach.gov.in');
  const [password, setPassword] = useState('demo-admin');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    setError('');
    apiLogin(email, password)
      .then((data) => {
        onLoginSuccess(data);
        navigate('/');
      })
      .catch(() => {
        setError('Authentication failed. Verify credentials.');
      });
  };

  return (
    <div className="page-container" style={{ maxWidth: 500, paddingTop: 60 }}>
      <div className="panel" style={{ borderTop: '4px solid #0f5c53' }}>
        <span className="eyebrow">AUTHORIZED STAKEHOLDER PORTAL</span>
        <h2 style={{ margin: '6px 0 16px' }}>Sign in to Taap Kavach Operations</h2>
        {error && <div style={{ background: '#fef2f2', color: '#b91c1c', padding: 8, borderRadius: 3, marginBottom: 12 }}>{error}</div>}

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Department / Organization Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border-color)', borderRadius: 3 }}
              required
            />
          </div>

          <div style={{ marginBottom: 18 }}>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Access Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border-color)', borderRadius: 3 }}
              required
            />
          </div>

          <button type="submit" className="btn-sm btn-primary" style={{ width: '100%', padding: 9, fontSize: 12 }}>
            Authenticate & Open Operations Console
          </button>
        </form>

        <div style={{ marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--border-light)', fontSize: 11, color: 'var(--text-muted)' }}>
          <b>Demo Stakeholder Accounts:</b>
          <div style={{ marginTop: 6 }}>
            <div>• <b>Municipal Admin:</b> admin.bhopal@taapkavach.gov.in / demo-admin</div>
            <div>• <b>Healthcare Facility:</b> healthcare.hospital@taapkavach.gov.in / demo-health</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 10. CHATBOT WIDGET
// ==========================================
function ChatbotWidget({ ward, alert, bundle }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      from: 'bot',
      text: `Namaste. I am your Taap Kavach heat assistant. You are currently viewing ${ward?.ward_name || 'Bhopal'} (${alert?.current_alert_level || 'Orange'} alert). Ask me about local risk factors, HTSI, 4-day forecast, or recommended actions.`,
    },
  ]);

  const context = {
    wardName: ward?.ward_name,
    alertLevel: alert?.current_alert_level,
    latest: bundle?.current?.weather,
    indices: bundle?.current?.thermal_metrics,
    htsi: bundle?.current?.thermal_metrics?.htsi,
    forecast: bundle?.forecast,
  };

  const handleSend = (text = input) => {
    if (!text.trim()) return;
    const reply = getChatbotReply(text, context);
    setMessages((prev) => [...prev, { from: 'user', text }, { from: 'bot', text: reply }]);
    setInput('');
  };

  return (
    <div className="chat-wrap">
      {open && (
        <div className="chat-panel">
          <div className="chat-head">
            <b>Taap Kavach Assistant</b>
            <button onClick={() => setOpen(false)}>×</button>
          </div>
          <div className="chat-prompts">
            {CHATBOT_PROMPTS.slice(0, 5).map((p, i) => (
              <button key={i} onClick={() => handleSend(p)}>{p}</button>
            ))}
          </div>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.from}`}>
                {m.text}
              </div>
            ))}
          </div>
          <div className="chat-input">
            <input
              placeholder="Ask about this ward or forecast..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button onClick={() => handleSend()}>Send</button>
          </div>
        </div>
      )}
      <button className="chat-button" onClick={() => setOpen(!open)}>
        <span>💬 Ask TK Assistant</span>
      </button>
    </div>
  );
}

// ==========================================
// ROOT APP COMPONENT
// ==========================================
function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('taap_user') || 'null'));
  const [activeTab, setActiveTab] = useState('overview');

  // Geographic Hierarchy State
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [cities, setCities] = useState([]);
  const [wards, setWards] = useState([]);

  const [stateId, setStateId] = useState('MP');
  const [districtId, setDistrictId] = useState('bhopal');
  const [cityId, setCityId] = useState('bhopal_bmc');
  const [wardId, setWardId] = useState('BPL_W003'); // Habibganj default high-risk ward

  // Active City and Ward Bundles
  const [citySummary, setCitySummary] = useState(null);
  const [bundle, setBundle] = useState(null);

  // Initialize Geographic Dropdowns
  useEffect(() => {
    getStates().then(setStates).catch(() => {});
    getDistricts(stateId).then(setDistricts).catch(() => {});
    getCities(districtId).then(setCities).catch(() => {});
    getWards(cityId).then((wList) => {
      setWards(wList);
      if (wList.length && !wList.some((w) => w.ward_id === wardId)) {
        setWardId(wList[0].ward_id);
      }
    }).catch(() => {});
  }, []);

  // Update dropdowns when State/District/City changes
  const handleGeoChange = (type, val) => {
    if (type === 'state') {
      setStateId(val);
      getDistricts(val).then((dList) => {
        setDistricts(dList);
        if (dList.length) handleGeoChange('district', dList[0].id);
      });
    } else if (type === 'district') {
      setDistrictId(val);
      getCities(val).then((cList) => {
        setCities(cList);
        if (cList.length) handleGeoChange('city', cList[0].id);
      });
    } else if (type === 'city') {
      setCityId(val);
      getWards(val).then((wList) => {
        setWards(wList);
        if (wList.length) setWardId(wList[0].ward_id);
      });
    } else if (type === 'ward') {
      setWardId(val);
    }
  };

  // Fetch City Summary whenever City changes
  useEffect(() => {
    getCitySummary(cityId).then(setCitySummary).catch(() => {});
  }, [cityId]);

  // Fetch Ward Bundle whenever Ward changes
  useEffect(() => {
    if (wardId) {
      getWardBundle(wardId).then(setBundle).catch(() => {});
    }
  }, [wardId]);

  const handleLogout = () => {
    apiLogout();
    setUser(null);
  };

  const selectedWard = wards.find((w) => w.ward_id === wardId) || wards[0];

  return (
    <Routes>
      <Route
        path="/login"
        element={<LoginPage onLoginSuccess={(userData) => setUser(userData)} />}
      />
      <Route
        path="*"
        element={
          <AppShell
            user={user}
            onLogout={handleLogout}
            geo={{ stateId, districtId, cityId, wardId, states, districts, cities, wards }}
            onGeoChange={handleGeoChange}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          >
            {activeTab === 'overview' && (
              <OverviewView
                citySummary={citySummary}
                onSelectWard={(wid) => { setWardId(wid); setActiveTab('forecast'); }}
                onNavigateTab={setActiveTab}
              />
            )}
            {activeTab === 'map' && (
              <HeatMapView
                wards={wards}
                selectedWardId={wardId}
                onSelectWard={setWardId}
                onNavigateTab={setActiveTab}
              />
            )}
            {activeTab === 'forecast' && (
              <WardForecastView
                bundle={bundle}
                onNavigateTab={setActiveTab}
              />
            )}
            {activeTab === 'risk' && (
              <RiskImpactView
                bundle={bundle}
                onNavigateTab={setActiveTab}
              />
            )}
            {activeTab === 'admin' && (
              <AdministrationView
                selectedWardId={wardId}
                onSelectWard={setWardId}
              />
            )}
            {activeTab === 'healthcare' && (
              <HealthcareView
                selectedWardId={wardId}
              />
            )}
            {activeTab === 'citizen' && (
              <CitizenView
                bundle={bundle}
              />
            )}
            {activeTab === 'methodology' && (
              <MethodologyView />
            )}

            <ChatbotWidget
              ward={selectedWard}
              alert={bundle?.alert}
              bundle={bundle}
            />
          </AppShell>
        }
      />
    </Routes>
  );
}

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);