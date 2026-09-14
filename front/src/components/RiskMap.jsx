import { useEffect } from 'react'
import { CircleMarker, MapContainer, Polygon, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const levelColor = {
  LOW: '#72c46b',
  MODERATE: '#e0b52f',
  HIGH: '#e17d37',
  CRITICAL: '#c94b3f',
}

function FocusLocation({ location }) {
  const map = useMap()
  useEffect(() => {
    if (location?.lat && location?.lon) {
      map.flyTo([location.lat, location.lon], Math.max(map.getZoom(), 7), { duration: 0.7 })
    }
  }, [location, map])
  return null
}

export default function RiskMap({ zones, selectedLocation }) {
  const center = selectedLocation?.lat && selectedLocation?.lon
    ? [selectedLocation.lat, selectedLocation.lon]
    : [27.4, 92.5]

  return (
    <MapContainer center={center} zoom={6} scrollWheelZoom className="risk-map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FocusLocation location={selectedLocation} />
      {zones.map((zone) => (
        <Polygon
          key={`${zone.location_id}-${zone.h3Cell || zone.h3_cell || zone.lat}`}
          positions={zone.h3Boundary || zone.h3_boundary || []}
          pathOptions={{
            color: levelColor[zone.level] || '#6f9aaa',
            fillColor: levelColor[zone.level] || '#6f9aaa',
            fillOpacity: 0.45,
            weight: 2,
          }}
        >
          <Popup>
            <strong>{zone.location_id}</strong><br />
            {zone.level} · {zone.score}/100<br />
            H3: {zone.h3Cell || zone.h3_cell || 'Unavailable'}<br />
            Priority: {zone.priority || 'Unavailable'}<br />
            Satellite evidence: {zone.satelliteEvidence?.length || 0}<br />
            {zone.satelliteEvidence?.some((item) => item.change_detected)
              ? 'Possible deformation signal detected'
              : 'No change flagged'}<br />
            {zone.data_provenance || 'Backend risk zone'}
          </Popup>
        </Polygon>
      ))}
      {zones.map((zone) => (
        <CircleMarker
          key={`point-${zone.location_id}`}
          center={[zone.lat, zone.lon]}
          radius={zone.location_id === selectedLocation?.id ? 7 : 4}
          pathOptions={{
            color: levelColor[zone.level] || '#6f9aaa',
            fillColor: levelColor[zone.level] || '#6f9aaa',
            fillOpacity: 0.95,
            weight: 2,
          }}
        />
      ))}
      {zones.flatMap((zone) => (zone.satelliteEvidence || []).map((evidence) => (
        <CircleMarker
          key={`satellite-${evidence.id}`}
          center={[evidence.latitude, evidence.longitude]}
          radius={8}
          pathOptions={{
            color: '#65c8e8',
            fillColor: '#65c8e8',
            fillOpacity: 0.85,
            weight: 2,
          }}
        >
          <Popup>
            <strong>Satellite evidence</strong><br />
            {evidence.platform} · {evidence.detection_type}<br />
            {evidence.change_detected
              ? 'Possible deformation signal detected'
              : 'No change flagged'}<br />
            {evidence.confidence !== null ? `Confidence: ${evidence.confidence}%` : 'Confidence unavailable'}<br />
            {evidence.data_status} · {evidence.is_simulated ? 'DEMO RECORD' : 'LIVE SOURCE'}
          </Popup>
        </CircleMarker>
      )))}
    </MapContainer>
  )
}
