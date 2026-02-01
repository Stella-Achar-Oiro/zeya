import { useState, useEffect } from 'react'
import { getOverview, getDangerAlerts } from '../services/api'
import {
  Users,
  MessageSquare,
  AlertTriangle,
  Clock,
  Activity,
  UserCheck,
} from 'lucide-react'

function StatCard({ icon: Icon, label, value, color = 'primary' }) {
  const colorMap = {
    primary: 'bg-primary-50 text-primary-700',
    blue: 'bg-blue-50 text-blue-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colorMap[color]}`}>
          <Icon size={24} />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [overview, setOverview] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [overviewRes, alertsRes] = await Promise.all([
          getOverview(),
          getDangerAlerts(10),
        ])
        setOverview(overviewRes.data)
        setAlerts(alertsRes.data)
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading dashboard...</p>
      </div>
    )
  }

  if (!overview) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Failed to load dashboard data.</p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard Overview</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <StatCard
          icon={Users}
          label="Total Users"
          value={overview.total_users}
          color="primary"
        />
        <StatCard
          icon={UserCheck}
          label="Active Users (7d)"
          value={overview.active_users_7d}
          color="blue"
        />
        <StatCard
          icon={MessageSquare}
          label="Conversations (7d)"
          value={overview.total_conversations_7d}
          color="primary"
        />
        <StatCard
          icon={Activity}
          label="Intervention Group"
          value={overview.intervention_users}
          color="blue"
        />
        <StatCard
          icon={AlertTriangle}
          label="Danger Sign Alerts"
          value={overview.danger_sign_alerts_pending}
          color="red"
        />
        <StatCard
          icon={Clock}
          label="Avg Response Time"
          value={
            overview.avg_response_time_ms
              ? `${Math.round(overview.avg_response_time_ms)}ms`
              : 'N/A'
          }
          color="amber"
        />
      </div>

      {/* Recent Danger Sign Alerts */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Danger Sign Alerts
        </h3>
        {alerts.length === 0 ? (
          <p className="text-gray-500 text-sm">No recent danger sign alerts.</p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 p-3 bg-red-50 rounded-lg"
              >
                <AlertTriangle size={18} className="text-red-600 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 break-words">
                    {alert.message_text}
                  </p>
                  <div className="flex gap-4 mt-1 text-xs text-gray-500">
                    <span>Phone: {alert.phone_number}</span>
                    {alert.gestational_age && (
                      <span>GA: {alert.gestational_age} weeks</span>
                    )}
                    <span>
                      {new Date(alert.created_at).toLocaleString()}
                    </span>
                  </div>
                  {alert.danger_sign_keywords && (
                    <p className="text-xs text-red-600 mt-1">
                      Keywords: {alert.danger_sign_keywords}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
