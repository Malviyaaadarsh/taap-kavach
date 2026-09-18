const format = (value, unit = '') => (value === undefined || value === null ? '--' : `${Number(value).toFixed(1)}${unit}`);

export const CHATBOT_PROMPTS = [
  'What is the current alert for this ward?',
  'Why is this ward at risk?',
  'What should outdoor workers do?',
  'Compare the hottest and coolest wards',
  'What is the forecast for the next five days?',
  'What do the alert colours mean?',
  'Explain WBGT and UTCI',
  'Where does this data come from?',
  'How confident is this forecast?',
  'What should a hospital prepare?',
  'What is Taap Kavach?',
];

const answerFor = (query, context) => {
  const text = query.trim().toLowerCase();
  const ward = context.wardName || 'the selected ward';
  const alert = context.alertLevel || 'being loaded';
  const latest = context.latest || {};
  const indices = context.indices || {};
  const forecast = context.forecast || [];
  const hottest = context.hottest;
  const coolest = context.coolest;

  if (/(where|source|real|data|updated|date)/.test(text)) {
    return 'This view uses the supplied MET Norway Bhopal snapshot for 14-18 September 2026, with ward-level offsets from the Taap Kavach analysis. It is a five-day evidence snapshot, not a live feed.';
  }
  if (/(why|reason|risk|hot|heat island|vegetation)/.test(text)) {
    return `${ward} is currently ${alert}. The latest reading is ${format(latest.temperature, ' C')} with ${format(latest.humidity, '%')} humidity; its thermal values are WBGT ${format(indices.wbgt, ' C')}, UTCI ${format(indices.utci, ' C')}, and Heat Index ${format(indices.heat_index, ' C')}. Ward characteristics such as density, vegetation, elevation, and local offsets influence the result.`;
  }
  if (/(compare|hottest|coolest|ranking)/.test(text)) {
    return hottest && coolest ? `In the supplied 18 September ward summary, ${hottest.ward_name} is hottest at ${format(hottest.temperature, ' C')} with ${hottest.alert_level} alert, while ${coolest.ward_name} is coolest at ${format(coolest.temperature, ' C')} with ${coolest.alert_level} alert. These are interpolated ward estimates, not official boundary observations.` : 'Ward comparison is available after the dashboard finishes loading.';
  }
  if (/(forecast|next five|tomorrow|predict)/.test(text)) {
    if (!forecast.length) return 'The five-day forecast is still loading.';
    const first = forecast[0];
    const last = forecast[forecast.length - 1];
    return `For ${ward}, the model forecast moves from ${first.predicted_alert_level} on ${first.date} to ${last.predicted_alert_level} on ${last.date}. Predicted UTCI ranges from ${format(first.predicted_utci, ' C')} to ${format(last.predicted_utci, ' C')}. This is a prototype forecast, not a guarantee.`;
  }
  if (/(worker|outdoor|delivery|construction)/.test(text)) return `${ward} is ${alert}. Outdoor workers should shift strenuous work toward cooler hours, take frequent shade and water breaks, use light protective clothing, and stop for symptoms such as dizziness, confusion, or unusual weakness.`;
  if (/(hospital|health|bed|fluid|clinic)/.test(text)) return `For a ${alert} ward, healthcare teams should check cooling equipment, IV fluid and ORS stock, heat-illness triage, staff briefings, and surge bed capacity. Taap Kavach provides preparedness information, not clinical instructions.`;
  if (/(elderly|older|senior|child|children|sick|chronic)/.test(text)) return `During ${alert} conditions in ${ward}, older adults, children, and people with chronic illness should avoid peak afternoon heat, stay hydrated, use a cool room, and have someone check on them.`;
  if (/(colour|color|alert level|green|yellow|orange|red)/.test(text)) return 'Green means normal monitoring; Yellow means precautions; Orange prioritises older adults, children, outdoor workers, and people with illness; Red means severe heat stress and avoiding non-essential outdoor activity.';
  if (/(wbgt|utci|heat index|calculated|thermal)/.test(text)) return 'WBGT describes occupational heat stress using humidity and radiant conditions. UTCI estimates perceived thermal stress. Heat Index describes temperature and humidity together. Taap Kavach uses UTCI for alert colour classification and shows all three for context.';
  if (/(confidence|accur|reliable|model)/.test(text)) return 'Forecast confidence is a prototype model confidence score. The current training window contains five days and 400 ward-interpolated hourly observations, so it must be validated against a longer historical series before operational use.';
  if (/(what is taap|about taap|who should use)/.test(text)) return 'Taap Kavach adds a ward/zone layer to the National, Regional, and District forecasting structure. It helps citizens, municipal teams, and healthcare facilities turn heat signals into local preparedness actions.';
  return `I can answer about ${ward}'s current alert, local risk factors, ward comparison, the five-day forecast, WBGT/UTCI, data provenance, or safety actions. Try one of the suggested questions.`;
};

export function getChatbotReply(query, context) {
  return answerFor(query, context);
}
