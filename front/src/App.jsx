import { useEffect, useMemo, useState } from 'react'
import {
  acknowledgeAlert, assignAlert, escalateAlert, getAlerts, getFieldReports, getHealth,
  getImpact, getIncidents, getLocations, getObservations, getPriority, getRisk,
  getRiskZones, getSatelliteObservations, inspectFieldReport, submitFieldReport,
} from './api'
import RiskMap from './components/RiskMap'

const emptyRisk = {
  location: { id: '', name: 'No location selected', lat: 27.4, lon: 92.5 },
  risk: { score: 0, level: 'UNKNOWN', trend: 'UNKNOWN' },
  factors: [], impact: {}, priority: 'P4',
}

const pathFor = () => window.location.pathname || '/'

function navigate(path) {
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

function App() {
  const [path, setPath] = useState(pathFor())
  const [mode, setMode] = useState(path.startsWith('/government') ? 'government' : 'public')
  const [locations, setLocations] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [risk, setRisk] = useState(null)
  const [impact, setImpact] = useState(null)
  const [zones, setZones] = useState([])
  const [observations, setObservations] = useState([])
  const [satellite, setSatellite] = useState([])
  const [alerts, setAlerts] = useState([])
  const [incidents, setIncidents] = useState([])
  const [priority, setPriority] = useState([])
  const [reports, setReports] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const onPopState = () => {
      const next = pathFor()
      setPath(next)
      setMode(next.startsWith('/government') ? 'government' : 'public')
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  async function loadLocation(id) {
    if (!id) return
    setSelectedId(id)
    const results = await Promise.allSettled([
      getRisk(id), getImpact(id), getObservations(id), getSatelliteObservations(id),
    ])
    const [riskResult, impactResult, observationResult, satelliteResult] = results
    if (riskResult.status === 'rejected') {
      if (riskResult.reason.status !== 404) throw riskResult.reason
      const location = locations.find((item) => item.id === id)
      setRisk({
        ...emptyRisk,
        location: location
          ? { id: location.id, name: location.name, lat: location.latitude, lon: location.longitude }
          : { id, name: `Observed event ${id.replace('REAL-EVENT-', '')}`, lat: emptyRisk.location.lat, lon: emptyRisk.location.lon },
      })
    } else {
      setRisk(riskResult.value)
    }
    setImpact(impactResult.status === 'fulfilled' ? impactResult.value : null)
    setObservations(observationResult.status === 'fulfilled' ? observationResult.value?.observations || [] : [])
    setSatellite(satelliteResult.status === 'fulfilled' ? satelliteResult.value?.observations || [] : [])
  }

  async function load() {
    setLoading(true)
    setError('')
    const results = await Promise.allSettled([
      getHealth(), getLocations(), getAlerts(), getIncidents(), getPriority(), getRiskZones(), getFieldReports(),
    ])
    const [healthResult, locationsResult, alertsResult, incidentsResult, priorityResult, zonesResult, reportsResult] = results
    if (healthResult.status === 'fulfilled') setHealth(healthResult.value)
    if (locationsResult.status === 'fulfilled') {
      const available = locationsResult.value?.locations || []
      setLocations(available)
      const id = selectedId || available[0]?.id
      if (id) {
        try { await loadLocation(id) } catch (requestError) { setError(requestError.message) }
      }
    }
    if (alertsResult.status === 'fulfilled') setAlerts(alertsResult.value?.alerts || [])
    if (incidentsResult.status === 'fulfilled') setIncidents(incidentsResult.value?.incidents || [])
    if (priorityResult.status === 'fulfilled') setPriority(priorityResult.value?.items || [])
    if (zonesResult.status === 'fulfilled') setZones(zonesResult.value?.zones || [])
    if (reportsResult.status === 'fulfilled') setReports(reportsResult.value?.reports || [])
    const failure = results.find((result) => result.status === 'rejected')
    if (failure) setError(`${failure.reason.message} (${failure.reason.path || 'startup request'})`)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const selectedLocation = useMemo(
    () => locations.find((location) => location.id === selectedId) || risk?.location || emptyRisk.location,
    [locations, selectedId, risk],
  )
  const displayRisk = risk || emptyRisk
  const switchMode = (nextMode) => {
    setMode(nextMode)
    navigate(nextMode === 'government' ? '/government' : '/')
  }
  const refreshReports = async () => {
    const response = await getFieldReports()
    setReports(response?.reports || [])
  }

  return (
    <div className={`app-shell ${mode}-theme`}>
      <Header mode={mode} health={health} onMode={switchMode} onRefresh={load} />
      {error && <div className="global-error"><strong>Data service issue.</strong> {error}<button onClick={load}>Retry</button></div>}
      {mode === 'government'
        ? <GovernmentDashboard path={path} loading={loading} locations={locations} selectedId={selectedId} onSelect={loadLocation} risk={displayRisk} impact={impact} zones={zones} observations={observations} satellite={satellite} alerts={alerts} incidents={incidents} priority={priority} reports={reports} setAlerts={setAlerts} refreshReports={refreshReports} onNavigate={navigate} />
        : <PublicDashboard path={path} locations={locations} selectedLocation={selectedLocation} risk={displayRisk} impact={impact} zones={zones} observations={observations} alerts={alerts} onSelect={loadLocation} onNavigate={navigate} />}
      <footer>For planning and awareness only — please follow SDMA and local authority advisories.</footer>
    </div>
  )
}

function Header({ mode, health, onMode, onRefresh }) {
  return <header className="topbar"><button className="brand" onClick={() => onMode('public')}><span className="brand-icon">▲</span><span>Landslide<strong>Guard</strong><small>LANDSLIDE RISK &amp; FIELD REPORTING</small></span></button><div className="mode-switch"><button className={mode === 'government' ? 'selected' : ''} onClick={() => onMode('government')}>Government &amp; Field</button><button className={mode === 'public' ? 'selected' : ''} onClick={() => onMode('public')}>Public &amp; Tourist</button></div><div className="top-actions"><span className={health?.status === 'ok' ? 'status online' : 'status'}><i />{health?.status === 'ok' ? 'Connected' : 'Service unavailable'}</span><button className="refresh" onClick={onRefresh}>↻ Refresh</button></div></header>
}

function GovernmentDashboard({ path, loading, locations, selectedId, onSelect, risk, impact, zones, observations, satellite, alerts, incidents, priority, reports, setAlerts, refreshReports, onNavigate }) {
  const section = path.split('/')[2] || 'overview'
  const highRisk = zones.filter((zone) => ['HIGH', 'CRITICAL'].includes(zone.level)).length
  const page = section === 'alerts' ? <AlertsPage alerts={alerts} onChanged={setAlerts} /> : section === 'incidents' ? <IncidentsPage incidents={incidents} /> : section === 'field' ? <FieldPage reports={reports} refreshReports={refreshReports} locations={locations} /> : section === 'satellite' ? <SatellitePage observations={satellite} /> : section === 'h3' ? <H3Page zones={zones} /> : section === 'reports' ? <ReportsPage reports={reports} risk={risk} observations={observations} satellite={satellite} /> : section === 'infrastructure' ? <InfrastructurePage impact={impact} /> : <><Kpis highRisk={highRisk} alerts={alerts} incidents={incidents} locations={locations} /><div className="command-grid"><section className="panel map-card"><div className="map-card-heading"><div><p className="eyebrow">RISK MAP</p><h2>Northeast India operational view</h2></div><span className="map-status">● UPDATED FROM AVAILABLE DATA</span></div><div className="map-frame"><RiskMap zones={zones} selectedLocation={risk.location} /></div></section><section className="panel"><PanelTitle title="Top high-risk locations" /><RankedLocations priority={priority} onSelect={onSelect} /></section></div><LocationPanel risk={risk} impact={impact} observations={observations} satellite={satellite} /></>
  return <><div className="government-shell"><aside className="sidebar"><button className="sidebar-brand" onClick={() => onNavigate('/government')}>▲ Landslide<strong>Guard</strong></button>{[['','⌂','Command Center'],['h3','⬡','H3 Risk Grid'],['alerts','!','Alerts'],['incidents','◉','Incidents'],['field','▣','Field Reports'],['satellite','◈','Satellite'],['infrastructure','▤','Infrastructure'],['reports','▤','Reports']].map(([id, icon, label]) => <button className={section === (id || 'overview') ? 'sidebar-link active' : 'sidebar-link'} key={label} onClick={() => onNavigate(id ? `/government/${id}` : '/government')}><span>{icon}</span>{label}</button>)}<div className="sidebar-status"><small>SYSTEM STATUS</small><b>● {loading ? 'Updating' : 'Connected'}</b><span>Data connection is active</span></div></aside><main className="government-main"><div className="page-heading"><div><p className="eyebrow">NORTHEAST INDIA / GOVERNMENT &amp; FIELD</p><h1>{section === 'overview' ? 'Command Center' : section.replace('-', ' ')}</h1><p className="muted">See the situation, understand the impact, and decide what to check next.</p></div><label>Monitored location<select value={selectedId} onChange={(event) => onSelect(event.target.value)}>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label></div>{page}</main></div></>
}

function Kpis({ highRisk, alerts, incidents, locations }) {
  return <div className="kpi-grid">{[['HIGH-RISK AREAS', highRisk, 'Risk zones returned'], ['OPEN ALERTS', alerts.length, 'Needs attention'], ['ONGOING INCIDENTS', incidents.filter((item) => !['RESOLVED', 'MONITORING'].includes(item.status)).length, 'Awaiting action'], ['MONITORED LOCATIONS', locations.length, 'Configured sites']].map(([label, value, note]) => <div className="kpi-card" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
}

function LocationPanel({ risk, impact, observations, satellite }) {
  return <div className="dashboard-grid"><section className="panel risk-panel"><PanelTitle title={risk.location.name} /><div className="score">{risk.risk.score}<small>/100</small></div><span className={`level ${risk.risk.level.toLowerCase()}`}>{risk.risk.level}</span><div className="risk-meta"><span>Trend <b>{risk.risk.trend}</b></span><span>Priority <b>{risk.priority}</b></span></div></section><section className="panel"><PanelTitle title="Why is this location risky?" /><div className="factor-list">{risk.factors.length ? risk.factors.map((factor) => <div className="factor" key={factor.name}><span>{factor.name}<small>{factor.value ?? '--'} {factor.unit || ''}</small></span><b>{factor.contribution} · {factor.direction}</b></div>) : <Empty text="No factor information available." />}</div></section><section className="panel"><PanelTitle title="Potentially exposed infrastructure" /><div className="impact-grid">{Object.entries(impact?.counts || risk.impact || {}).map(([key, value]) => <div key={key}><strong>{value}</strong><span>{key.replaceAll('_', ' ')}</span></div>)}</div><p className="muted">Exposure does not mean damage or blockage.</p></section><section className="panel"><PanelTitle title="Evidence" /><p className="muted">{observations.length} environmental observations · {satellite.length} satellite observations</p>{satellite.some((item) => item.change_detected) && <div className="evidence-note">Possible deformation signal detected — not a confirmed landslide.</div>}</section></div>
}

function AlertsPage({ alerts, onChanged }) {
  const action = async (alert, type) => {
    try {
      const response = type === 'acknowledge' ? await acknowledgeAlert(alert.id, 'State EOC') : type === 'assign' ? await assignAlert(alert.id, 'SDMA Field Team') : await escalateAlert(alert.id, 'Escalated by State EOC')
      onChanged(alerts.map((item) => item.id === alert.id ? response : item))
    } catch (error) { window.alert(error.message) }
  }
  return <section className="panel page-panel"><PanelTitle title="Operational alerts" /><div className="alert-list">{alerts.length ? alerts.map((alert) => <article className="alert-card" key={alert.id}><div><span className={`level ${alert.severity.toLowerCase()}`}>{alert.severity}</span><b>{alert.location_id}</b><p>{alert.reason}</p><small>{alert.status} · {alert.action}</small></div><div className="button-row"><button onClick={() => action(alert, 'acknowledge')}>Acknowledge</button><button onClick={() => action(alert, 'assign')}>Assign</button><button onClick={() => action(alert, 'escalate')}>Escalate</button></div></article>) : <Empty text="No alerts returned." />}</div></section>
}

function IncidentsPage({ incidents }) { return <section className="panel page-panel"><PanelTitle title="Incident workflow" /><div className="table-list">{incidents.length ? incidents.map((incident) => <div className="queue-row" key={incident.id}><span><b>{incident.priority}</b> {incident.location_id}</span><span>{incident.status}</span></div>) : <Empty text="No incidents returned." />}</div></section> }
function H3Page({ zones }) { return <section className="panel page-panel"><PanelTitle title="H3 risk grid" /><p className="muted">H3 answers where the assessed risk is located; the risk score remains the backend decision-support result.</p><div className="h3-grid-list">{zones.length ? zones.map((zone) => <div className="queue-row" key={zone.h3Cell || zone.h3_cell || zone.location_id}><span><b>{zone.h3Cell || zone.h3_cell || 'Unavailable'}</b> {zone.location_id}<small>{zone.level} · {zone.score}/100 · {zone.trend}</small></span><span>{zone.priority}<br />{zone.data_provenance}</span></div>) : <Empty text="No H3 risk cells available." />}</div></section> }
function SatellitePage({ observations }) { return <section className="panel page-panel"><PanelTitle title="Satellite evidence" /><div className="table-list">{observations.length ? observations.map((item) => <div className="queue-row" key={item.id}><span><b>{item.platform}</b> {item.product_type}</span><span>{item.change_detected ? 'Possible change' : 'No change flagged'} · {item.is_demo ? 'DEMO' : 'SOURCE'}</span></div>) : <Empty text="No satellite observations available." />}</div></section> }
function InfrastructurePage({ impact }) { return <section className="panel page-panel"><PanelTitle title="Infrastructure exposure" /><p className="muted">Potentially exposed assets, not confirmed damage.</p><div className="table-list">{impact?.potentially_exposed?.length ? impact.potentially_exposed.map((asset) => <div className="queue-row" key={asset.id}><span><b>{asset.asset_type}</b> {asset.name}</span><span>{asset.distance_km} km · {asset.is_demo ? 'DEMO' : 'SOURCE'}</span></div>) : <Empty text="No infrastructure assets available for the selected location." />}</div></section> }
function ReportsPage({ reports, risk, observations, satellite }) { const exportReport = () => { const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([JSON.stringify({ generated_at: new Date().toISOString(), risk, reports, observations, satellite }, null, 2)], { type: 'application/json' })); link.download = `${risk.location.id || 'site'}-report.json`; link.click() }; return <section className="panel page-panel"><PanelTitle title="Operational reports" /><p className="muted">{reports.length} field reports available for review.</p><button className="primary-button" onClick={exportReport}>Export site report</button></section> }
function FieldPage({ reports, refreshReports, locations }) { const [form, setForm] = useState({ location_id: locations[0]?.id || '', reporter_type: 'FIELD_TEAM', observation: '' }); const [message, setMessage] = useState(''); const submit = async (event) => { event.preventDefault(); try { await submitFieldReport(form); setMessage('Report submitted for field review.'); setForm({ ...form, observation: '' }); await refreshReports() } catch (error) { setMessage(error.message) } }; const inspect = async (report) => { const outcome = window.prompt('Enter CONFIRMED_DISASTER or FALSE_ALARM'); if (!outcome) return; try { await inspectFieldReport(report.id, { inspector: 'SDMA Operator', outcome, findings: 'Inspection recorded from field operations.', follow_up_action: outcome === 'CONFIRMED_DISASTER' ? 'Escalate response and inspect exposed infrastructure.' : 'Close as false alarm and continue monitoring.' }); await refreshReports() } catch (error) { setMessage(error.message) } }; return <div className="page-stack"><section className="panel"><PanelTitle title="Field operations" /><div className="verification-flow">RISK REVIEW <i>↓</i> ALERT <i>↓</i> FIELD VISIT <i>↓</i> GROUND CHECK <i>↓</i> REPORT</div><form className="report-form" onSubmit={submit}><select value={form.location_id} onChange={(event) => setForm({ ...form, location_id: event.target.value })}>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select><input value={form.reporter_type} onChange={(event) => setForm({ ...form, reporter_type: event.target.value })} placeholder="Reporter type" /><textarea required value={form.observation} onChange={(event) => setForm({ ...form, observation: event.target.value })} placeholder="Describe cracks, slope condition, road, drainage or seepage..." /><button className="primary-button">Submit field report</button></form>{message && <p className="action-notice">{message}</p>}</section><section className="panel"><PanelTitle title="Reports awaiting or completing verification" /><div className="table-list">{reports.length ? reports.map((report) => <div className="field-row" key={report.id}><span><b>{report.location_id}</b><br />{report.observation}</span><span>{report.inspection?.outcome || 'PENDING'}{!report.inspection && <button onClick={() => inspect(report)}>Record inspection</button>}</span></div>) : <Empty text="No field reports returned." />}</div></section></div> }
function PublicDashboard({ locations, selectedLocation, risk, impact, zones, observations, alerts, onSelect, onNavigate }) { const values = observations.flatMap((item) => Object.entries(item.values || {})); const find = (names) => values.find(([key]) => names.some((name) => key.toLowerCase().includes(name)))?.[1]; return <><div className="public-hero"><p className="eyebrow">NORTHEAST INDIA / PUBLIC &amp; TOURIST</p><h1>Explore safely.</h1><p>Check assessed landslide risk and environmental conditions before travelling.</p><div className="public-selector"><input placeholder="Search destination..." /><select value={selectedLocation.id} onChange={(event) => onSelect(event.target.value)}>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></div></div><main className="public-main"><section className="public-summary"><div className="public-risk-card"><span className={`level ${risk.risk.level.toLowerCase()}`}>{risk.risk.level === 'UNKNOWN' ? 'ASSESSMENT UNAVAILABLE' : `${risk.risk.level} RISK`}</span><strong>{risk.risk.level === 'UNKNOWN' ? '--' : risk.risk.score}<small>{risk.risk.level === 'UNKNOWN' ? '' : '/100'}</small></strong><h2>{selectedLocation.name}</h2><p>{risk.risk.level === 'UNKNOWN' ? 'Real environmental observations are available, but no verified risk assessment has been published for this location.' : 'Operational assessment based on available rainfall, terrain, exposure and field evidence.'}</p></div><div className="public-advisory"><h2>Travel advisory</h2><p>{risk.risk.level === 'UNKNOWN' ? 'Use the available weather conditions with official government advisories. This service has not assigned a risk level here.' : `${risk.risk.level} assessed risk. Follow official government advisories and avoid unstable slopes during heavy rainfall.`}</p><button onClick={() => onNavigate('/advisory')}>Read advisory</button></div></section><section className="public-grid"><div className="panel public-map"><PanelTitle title="Risk map" /><RiskMap zones={zones} selectedLocation={risk.location} /></div><div className="panel"><PanelTitle title="Conditions" /><div className="public-stats"><b>{find(['rainfall', 'precipitation']) ?? '--'} <small>mm rainfall</small></b><b>{find(['moisture', 'saturation']) ?? '--'} <small>soil moisture</small></b><b>{impact?.potentially_exposed?.length ?? 0} <small>potentially exposed assets</small></b></div><PanelTitle title="Safety guide" /><ul className="safety-list"><li>Avoid unstable slopes during heavy rain.</li><li>Do not stop unnecessarily below steep slopes.</li><li>Follow official advisories before travelling.</li><li>Report cracks, rockfall or seepage.</li></ul><button className="primary-button" onClick={() => onNavigate('/report')}>Report an incident</button></div></section><section className="panel"><PanelTitle title="Recent updates" />{alerts.slice(0, 3).map((alert) => <div className="queue-row" key={alert.id}><span><b>{alert.severity}</b> {alert.location_id}</span><span>{alert.reason}</span></div>)}{!alerts.length && <Empty text="No alerts returned." />}</section></main></> }

function PanelTitle({ title }) { return <div className="panel-heading"><h2>{title}</h2></div> }
function RankedLocations({ priority, onSelect }) { return priority.length ? <div className="table-list">{priority.slice(0, 8).map((item, index) => <button className="rank-row" key={item.location_id} onClick={() => onSelect(item.location_id)}><b>{index + 1}</b><span>{item.location_id}</span><strong>{item.score} · {item.priority}</strong></button>)}</div> : <Empty text="No priority locations returned." /> }
function Empty({ text }) { return <p className="empty-state">{text}</p> }

export default App
