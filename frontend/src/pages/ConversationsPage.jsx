import { useState, useEffect } from 'react'
import { getConversations } from '../services/api'
import { Link } from 'react-router-dom'

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [dangerOnly, setDangerOnly] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchConversations() {
      setLoading(true)
      try {
        const params = { page, page_size: 50 }
        if (dangerOnly) params.danger_signs_only = true
        const res = await getConversations(params)
        setConversations(res.data.conversations)
        setTotal(res.data.total)
      } catch (err) {
        console.error('Failed to fetch conversations:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchConversations()
  }, [page, dangerOnly])

  const totalPages = Math.ceil(total / 50)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Conversations</h2>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={dangerOnly}
            onChange={(e) => {
              setDangerOnly(e.target.checked)
              setPage(1)
            }}
            className="rounded border-gray-300"
          />
          Danger signs only
        </label>
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Direction
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Message
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                GA
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Danger
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Time
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : conversations.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  No conversations found.
                </td>
              </tr>
            ) : (
              conversations.map((conv) => (
                <tr key={conv.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        conv.message_direction === 'incoming'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-green-100 text-green-700'
                      }`}
                    >
                      {conv.message_direction}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-800 max-w-md truncate">
                    {conv.message_text}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <Link
                      to={`/users/${conv.user_id}`}
                      className="text-primary-600 hover:text-primary-800"
                    >
                      View User
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {conv.gestational_age_at_message
                      ? `${conv.gestational_age_at_message}w`
                      : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {conv.danger_sign_detected && (
                      <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-medium">
                        ALERT
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(conv.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t bg-gray-50">
            <p className="text-sm text-gray-500">
              Page {page} of {totalPages} ({total} total)
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border rounded text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
