import { useState, useEffect } from 'react'
import {
  getEngagementTrends,
  exportConversations,
  exportEngagement,
  exportAssessments,
} from '../services/api'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { Download } from 'lucide-react'

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

export default function AnalyticsPage() {
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState('')

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getEngagementTrends(12)
        setTrends(res.data)
      } catch (err) {
        console.error('Failed to fetch analytics:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleExport = async (type) => {
    setExporting(type)
    try {
      let res
      let filename
      switch (type) {
        case 'conversations':
          res = await exportConversations()
          filename = 'conversations_export.csv'
          break
        case 'engagement':
          res = await exportEngagement()
          filename = 'engagement_export.csv'
          break
        case 'assessments':
          res = await exportAssessments()
          filename = 'assessments_export.csv'
          break
        default:
          return
      }
      downloadBlob(new Blob([res.data]), filename)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExporting('')
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h2>

      {/* Engagement Trends Chart */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Weekly Engagement Trends
        </h3>
        {loading ? (
          <p className="text-gray-500 text-sm">Loading chart data...</p>
        ) : (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" label={{ value: 'Week', position: 'bottom' }} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="total_messages"
                stroke="#16a34a"
                name="Messages"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="active_users"
                stroke="#2563eb"
                name="Active Users"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Response Time Chart */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Average Response Time by Week
        </h3>
        {loading ? (
          <p className="text-gray-500 text-sm">Loading chart data...</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis label={{ value: 'ms', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Bar
                dataKey="avg_response_time"
                fill="#f59e0b"
                name="Avg Response Time (ms)"
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Data Export */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Data Export
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          Export anonymized research data in CSV format. Phone numbers are replaced
          with study IDs for privacy compliance.
        </p>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => handleExport('conversations')}
            disabled={!!exporting}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            <Download size={16} />
            {exporting === 'conversations'
              ? 'Exporting...'
              : 'Export Conversations'}
          </button>
          <button
            onClick={() => handleExport('engagement')}
            disabled={!!exporting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Download size={16} />
            {exporting === 'engagement'
              ? 'Exporting...'
              : 'Export Engagement Metrics'}
          </button>
          <button
            onClick={() => handleExport('assessments')}
            disabled={!!exporting}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 transition-colors"
          >
            <Download size={16} />
            {exporting === 'assessments'
              ? 'Exporting...'
              : 'Export Assessments (SPSS)'}
          </button>
        </div>
      </div>
    </div>
  )
}
