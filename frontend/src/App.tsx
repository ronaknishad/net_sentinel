import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Overview from './pages/Overview'
import TrafficExplorer from './pages/TrafficExplorer'
import Alerts from './pages/Alerts'
import ModelEvaluation from './pages/ModelEvaluation'
import DatasetManagement from './pages/DatasetManagement'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Overview />} />
        <Route path="traffic" element={<TrafficExplorer />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="evaluation" element={<ModelEvaluation />} />
        <Route path="datasets" element={<DatasetManagement />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
