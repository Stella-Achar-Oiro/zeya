import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getUsers } from '../services/api'

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [studyGroup, setStudyGroup] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchUsers() {
      setLoading(true)
      try {
        const params = { page, page_size: 20 }
        if (studyGroup) params.study_group = studyGroup
        const res = await getUsers(params)
        setUsers(res.data.users)
        setTotal(res.data.total)
      } catch (err) {
        console.error('Failed to fetch users:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchUsers()
  }, [page, studyGroup])

  const totalPages = Math.ceil(total / 20)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Users</h2>
        <select
          value={studyGroup}
          onChange={(e) => {
            setStudyGroup(e.target.value)
            setPage(1)
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Groups</option>
          <option value="intervention">Intervention</option>
          <option value="control">Control</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Phone
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Study Group
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Gestational Age
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Enrolled
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
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm">
                    <Link
                      to={`/users/${user.id}`}
                      className="text-primary-600 hover:text-primary-800 font-medium"
                    >
                      {user.name || 'Unnamed'}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {user.phone_number}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        user.study_group === 'intervention'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {user.study_group}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {user.current_gestational_age
                      ? `${user.current_gestational_age} weeks`
                      : 'N/A'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        user.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(user.enrolled_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t bg-gray-50">
            <p className="text-sm text-gray-500">
              Showing page {page} of {totalPages} ({total} total users)
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
