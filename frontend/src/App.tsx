import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Login from './pages/Login'
import PatientChat from './pages/patient/Chat'
import PatientHistory from './pages/patient/History'
import PatientProfile from './pages/patient/Profile'
import PatientCarePlan from './pages/patient/CarePlan'
import PatientMedicalRecord from './pages/patient/MedicalRecord'
import PatientReportDetail from './pages/patient/ReportDetail'
import PatientRegistration from './pages/patient/Registration'
import DoctorChat from './pages/doctor/Chat'
import DoctorSearch from './pages/doctor/Search'
import DoctorPatientRecord from './pages/doctor/PatientRecord'
import DoctorSearchHistory from './pages/doctor/SearchHistory'
import DoctorKnowledgeBase from './pages/doctor/KnowledgeBase'
import DoctorProfile from './pages/doctor/Profile'
import DoctorPatientList from './pages/doctor/PatientList'

function ProtectedRoute({ children, role }: { children: React.ReactNode; role?: string }) {
  const { token, user } = useAuthStore()
  if (!token) return <Navigate to="/login" replace />
  if (role && user?.role !== role) return <Navigate to={`/${user?.role}`} replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/patient/*"
        element={
          <ProtectedRoute role="patient">
            <Routes>
              <Route path="/chat" element={<PatientChat />} />
              <Route path="/history" element={<PatientHistory />} />
              <Route path="/profile" element={<PatientProfile />} />
              <Route path="/care-plan" element={<PatientCarePlan />} />
              <Route path="/medical-record" element={<PatientMedicalRecord />} />
              <Route path="/registration" element={<PatientRegistration />} />
              <Route path="/report/:reportId" element={<PatientReportDetail />} />
              <Route path="/" element={<Navigate to="/patient/chat" replace />} />
              <Route path="*" element={<Navigate to="/patient/chat" replace />} />
            </Routes>
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/*"
        element={
          <ProtectedRoute role="doctor">
            <Routes>
              <Route path="/chat" element={<DoctorChat />} />
              <Route path="/search" element={<DoctorSearch />} />
              <Route path="/patient/:patientId" element={<DoctorPatientRecord />} />
              <Route path="/search-history" element={<DoctorSearchHistory />} />
              <Route path="/patients" element={<DoctorPatientList />} />
              <Route path="/profile" element={<DoctorProfile />} />
              <Route path="/knowledge-base" element={<DoctorKnowledgeBase />} />
              <Route path="/" element={<Navigate to="/doctor/chat" replace />} />
              <Route path="*" element={<Navigate to="/doctor/chat" replace />} />
            </Routes>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
