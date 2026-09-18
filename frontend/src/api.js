import axios from 'axios';

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api' });
api.interceptors.request.use((config) => { const token = localStorage.getItem('taap_token'); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });
export const getWards = () => api.get('/bhopal/wards').then((r) => r.data);
export const getWardBundle = (id) => Promise.all([api.get(`/ward/${id}/weather?days_back=5`), api.get(`/ward/${id}/thermal-indices?days_back=5`), api.get(`/ward/${id}/forecast?days_ahead=5`), api.get(`/ward/${id}/alert-status`)]).then(([weather, thermal, forecast, alert]) => ({ weather: weather.data.weather_data, thermal: thermal.data.thermal_indices, forecast: forecast.data.forecast, alert: alert.data }));
export const login = (email, password) => api.post('/auth/login', { email, password }).then((r) => { localStorage.setItem('taap_token', r.data.access_token); localStorage.setItem('taap_user', JSON.stringify(r.data)); return r.data; });
export const getAdmin = (id) => api.get(`/admin/municipality-suggestions?ward_id=${id}`).then((r) => r.data);
export const getHealthcare = (id) => api.get(`/healthcare/hospital-readiness?ward_id=${id}`).then((r) => r.data);
export default api;
