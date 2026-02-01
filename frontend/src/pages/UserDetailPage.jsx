import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getUser, getConversations, deactivateUser } from '../services/api'

export default function UserDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [userRes, convRes] = await Promise.all([
          getUser(id),
          getConversations({ user_id: id, page_size: 100 }),
        ])
        setUser(userRes.data)
        setConversations(convRes.data.conversations)
      } catch (err) {
        console.error('Failed to fetch user data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [id])

  const handleDeactivate = async () => {
    if (!window.confirm('Are you sure you want to deactivate this user?')) return
    try {
      await deactivateUser(id)
      setUser((prev) => ({ ...prev, is_active: false }))
    } catch (err) {
      console.error('Failed to deactivate user:', err)
    }
  }

  if (loading) {
    return <p className="text-gray-500">Loading user details...</p>
  }

  if (!user) {
    return <p className="text-red-500">User not found.</p>
  }

  return (
    <div>
      <button
        onClick={() => navigate('/users')}
        className="text-sm text-primary-600 hover:text-primary-800 mb-4 inline-block"
      >
        &larr; Back to Users
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Profile */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            User Profile
          </h3>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-gray-500">Name</dt>
              <dd className="font-medium">{user.name || 'Unnamed'}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Phone</dt>
              <dd className="font-medium">{user.phone_number}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Study Group</dt>
              <dd className="font-medium capitalize">{user.study_group}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Gestational Age</dt>
              <dd className="font-medium">
                {user.current_gestational_age
                  ? `${user.current_gestational_age} weeks`
                  : 'Not set'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Expected Delivery</dt>
              <dd className="font-medium">
                {user.expected_delivery_date
                  ? new Date(user.expected_delivery_date).toLocaleDateString()
                  : 'N/A'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Status</dt>
              <dd>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    user.is_active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Enrolled</dt>
              <dd className="font-medium">
                {new Date(user.enrolled_at).toLocaleString()}
              </dd>
            </div>
          </dl>

          {user.is_active && (
            <button
              onClick={handleDeactivate}
              className="mt-6 w-full px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors"
            >
              Deactivate User
            </button>
          )}
        </div>

        {/* Conversation History */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Conversation History ({conversations.length} messages)
          </h3>
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {conversations.length === 0 ? (
              <p className="text-gray-500 text-sm">No conversations yet.</p>
            ) : (
              [...conversations].reverse().map((msg) => (
                <div
                  key={msg.id}
                  className={`p-3 rounded-lg text-sm ${
                    msg.message_direction === 'incoming'
                      ? 'bg-gray-100 mr-12'
                      : 'bg-primary-50 ml-12'
                  } ${msg.danger_sign_detected ? 'border-2 border-red-300' : ''}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-500">
                      {msg.message_direction === 'incoming' ? 'User' : 'Bot'}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(msg.created_at).toLocaleString()}
                    </span>
                    {msg.danger_sign_detected && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                        Danger Sign
                      </span>
                    )}
                  </div>
                  <p className="text-gray-800 whitespace-pre-wrap">
                    {msg.message_text}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
