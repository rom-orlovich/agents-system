import React, { useEffect, useState } from 'react'

interface Analytics {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  avg_duration_seconds: number
}

function Dashboard() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)

  useEffect(() => {
    fetch('/api/v1/analytics/summary')
      .then(res => res.json())
      .then(data => setAnalytics(data))
      .catch(err => console.error(err))
  }, [])

  return (
    <div style={{ padding: '20px' }}>
      <h1>Agent Dashboard</h1>
      {analytics && (
        <div>
          <h2>Statistics</h2>
          <p>Total Tasks: {analytics.total_tasks}</p>
          <p>Completed: {analytics.completed_tasks}</p>
          <p>Failed: {analytics.failed_tasks}</p>
          <p>Avg Duration: {analytics.avg_duration_seconds}s</p>
        </div>
      )}
    </div>
  )
}

export default Dashboard
