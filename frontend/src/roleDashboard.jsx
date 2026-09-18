import React, { useEffect, useState } from 'react';
import { getAdmin, getHealthcare } from './api';

const pretty = (key) => key.replaceAll('_', ' ');

function RoleMetric({ label, value, detail }) {
  return <div className="role-metric"><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
}

function AdministrationBriefing({ ward, alert, data }) {
  const hot = alert?.current_alert_level === 'Red' || alert?.current_alert_level === 'Orange';
  return <section className="role-workspace admin-workspace"><div className="workspace-heading"><div><span className="eyebrow">LOCAL ADMINISTRATION WORKSPACE</span><h2>Ward action briefing</h2><p>{ward?.ward_name || 'Selected ward'} · {ward?.zone || 'Bhopal'} zone · recommendations update with the selected alert.</p></div><span className={`workspace-status ${hot ? 'urgent' : 'watch'}`}>{hot ? 'Action required' : 'Monitor'}</span></div><div className="role-metrics"><RoleMetric label="Current signal" value={alert?.current_alert_level || '--'} detail="selected ward"/><RoleMetric label="Cooling capacity" value={data?.suggested_cooling_centers?.reduce((sum, item) => sum + item.capacity, 0) || '--'} detail="suggested seats"/><RoleMetric label="High-risk locations" value={data?.high_risk_areas?.length || '--'} detail="representative areas"/><RoleMetric label="SMS status" value={data?.sms_alert_simulation?.status || 'READY'} detail="simulation only"/></div><div className="workspace-columns"><div className="workspace-list"><h3>Immediate municipal actions</h3><ul><li>{data?.recommended_work_hour_adjustments || 'Review outdoor work hours and water-break policy.'}</li><li>{data?.resource_deployment_recommendations || 'Position water and ORS resources near high-footfall areas.'}</li><li>{data?.grid_load_management_tips || 'Prioritise reliable supply for cooling centres.'}</li></ul></div><div className="workspace-list"><h3>Suggested cooling points</h3>{data?.suggested_cooling_centers?.map((center) => <div className="recommendation-row" key={center.location}><b>{center.location}</b><span>{center.capacity} persons</span></div>) || <span>Loading ward recommendations...</span>}<p className="workspace-note">Prototype recommendations only. No municipal infrastructure is controlled by this system.</p></div></div></section>;
}

function HealthcareBriefing({ ward, alert, data }) {
  const level = alert?.current_alert_level || 'Green';
  const uplift = data?.predicted_patient_load_increase;
  return <section className="role-workspace health-workspace"><div className="workspace-heading"><div><span className="eyebrow">HEALTHCARE FACILITY WORKSPACE</span><h2>Heat-health readiness briefing</h2><p>{ward?.ward_name || 'Selected ward'} · prepared for {data?.hospital_id || 'served facility'} · values are planning estimates.</p></div><span className={`workspace-status ${level === 'Red' || level === 'Orange' ? 'urgent' : 'watch'}`}>{level} ward</span></div><div className="role-metrics"><RoleMetric label="Patient-load uplift" value={uplift === undefined ? '--' : `${uplift}%`} detail="prototype estimate"/><RoleMetric label="Recommended beds" value={data?.recommended_bed_capacity || '--'} detail="planning capacity"/><RoleMetric label="Priority groups" value={data?.risk_groups?.length || '--'} detail="groups to brief"/><RoleMetric label="Alert window" value="24 h" detail="review cycle"/></div><div className="workspace-columns"><div className="workspace-list"><h3>Readiness checklist</h3>{data?.priority_care_items?.slice(0, 4).map((item) => <label className="readiness-item" key={item}><input type="checkbox" defaultChecked/>{item}</label>) || <span>Loading readiness items...</span>}</div><div className="workspace-list"><h3>Clinical operations note</h3><div className="operations-callout"><b>{level === 'Red' ? 'Escalate heat protocol review today.' : 'Review readiness before the next update.'}</b><p>Check cooling equipment, IV fluid and ORS stock, heat-illness triage, staff briefing, and transport readiness.</p></div><p className="workspace-note">Planning support only. This dashboard is not a medical diagnosis or clinical command system.</p></div></div></section>;
}

export default function RoleDashboard({ user, ward, alert, bundle }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!user?.user_type || !ward?.ward_id) return;
    const request = user.user_type === 'local_administration' ? getAdmin(ward.ward_id) : getHealthcare(ward.ward_id);
    request.then(setData).catch(() => setData({ error: 'Role recommendations are temporarily unavailable.' }));
  }, [user?.user_type, ward?.ward_id, alert?.current_alert_level]);
  if (!user) return null;
  return user.user_type === 'local_administration'
    ? <AdministrationBriefing ward={ward} alert={alert} data={data || {}}/>
    : user.user_type === 'healthcare_facility'
      ? <HealthcareBriefing ward={ward} alert={alert} data={data || {}}/>
      : null;
}
