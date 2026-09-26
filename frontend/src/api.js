import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('taap_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Geographic Hierarchy
export const getStates = () => api.get('/locations/states').then((r) => r.data.states);
export const getDistricts = (stateId = 'MP') => api.get(`/locations/districts?state_id=${stateId}`).then((r) => r.data.districts);
export const getCities = (districtId = 'bhopal') => api.get(`/locations/cities?district_id=${districtId}`).then((r) => r.data.cities);
export const getWards = (cityId = 'bhopal_bmc') => api.get(`/locations/wards?city_id=${cityId}`).then((r) => r.data.wards);

// City Overview
export const getCitySummary = (cityId = 'bhopal_bmc') => api.get(`/city/${cityId}/summary`).then((r) => r.data);
export const getCityRiskMap = (cityId = 'bhopal_bmc') => api.get(`/city/${cityId}/risk-map`).then((r) => r.data);

// Ward Intelligence
export const getWardCurrent = (wardId) => api.get(`/ward/${wardId}/current`).then((r) => r.data);
export const getWardHistory = (wardId, daysBack = 10) => api.get(`/ward/${wardId}/history?days_back=${daysBack}`).then((r) => r.data);
export const getWardForecast = (wardId, daysAhead = 4) => api.get(`/ward/${wardId}/forecast?days_ahead=${daysAhead}`).then((r) => r.data);
export const getWardRisk = (wardId) => api.get(`/ward/${wardId}/risk`).then((r) => r.data);
export const getWardRecommendations = (wardId) => api.get(`/ward/${wardId}/recommendations`).then((r) => r.data);
export const getWardSeasonalWindows = (wardId) => api.get(`/ward/${wardId}/seasonal-windows`).then((r) => r.data);

// Comprehensive Ward Data Bundle for synchronous UI loading
export const getWardBundle = (id) =>
  Promise.all([
    getWardCurrent(id),
    getWardHistory(id, 10),
    getWardForecast(id, 4),
    getWardRisk(id),
    getWardRecommendations(id),
    getWardSeasonalWindows(id),
  ]).then(([current, history, forecast, risk, recs, seasonal]) => ({
    current,
    history: history.history,
    forecast: forecast.forecast,
    forecastMeta: forecast,
    risk,
    recommendations: recs,
    seasonal: seasonal.seasonal_comparison,
    alert: current.alert,
    weather: history.history,
    thermal: history.history,
  }));

// Administration & Healthcare Workspaces
export const getAdminOverview = () => api.get('/admin/overview').then((r) => r.data);
export const getAdminActions = (wardId) => api.get(`/admin/actions?ward_id=${wardId}`).then((r) => r.data);
export const getHealthcareOverview = () => api.get('/healthcare/overview').then((r) => r.data);
export const getHealthcareReadiness = (wardId) => api.get(`/healthcare/readiness?ward_id=${wardId}`).then((r) => r.data);
export const getMethodology = () => api.get('/methodology').then((r) => r.data);

// Legacy role getters
export const getAdmin = (id) => api.get(`/admin/actions?ward_id=${id}`).then((r) => r.data);
export const getHealthcare = (id) => api.get(`/healthcare/readiness?ward_id=${id}`).then((r) => r.data);

// Auth & Chat
export const login = (email, password) =>
  api.post('/auth/login', { email, password }).then((r) => {
    localStorage.setItem('taap_token', r.data.access_token);
    localStorage.setItem('taap_user', JSON.stringify(r.data));
    return r.data;
  });

export const logout = () => {
  localStorage.removeItem('taap_token');
  localStorage.removeItem('taap_user');
};

export const chatWithAssistant = (question, wardId) =>
  api.post('/chat', { question, ward_id: wardId }).then((r) => r.data);

export default api;
