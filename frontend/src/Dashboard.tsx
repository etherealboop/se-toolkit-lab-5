import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
)

const STORAGE_KEY = 'api_key'

interface ScoreBucket {
  bucket: string
  count: number
}

interface ScoresResponse {
  lab_id: string
  buckets: ScoreBucket[]
}

interface TimelineEntry {
  date: string
  submissions: number
}

interface TimelineResponse {
  lab_id: string
  data: TimelineEntry[]
}

interface PassRateEntry {
  task_id: string
  task_title: string
  pass_rate: number
  total_submissions: number
  passed_submissions: number
}

interface PassRatesResponse {
  lab_id: string
  tasks: PassRateEntry[]
}

interface LabOption {
  id: string
  name: string
}

const LABS: LabOption[] = [
  { id: 'lab-04', name: 'Lab 04' },
  { id: 'lab-05', name: 'Lab 05' },
  { id: 'lab-06', name: 'Lab 06' },
]

type FetchState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; message: string }

function Dashboard() {
  const [selectedLab, setSelectedLab] = useState<string>(LABS[0].id)
  const [scoresState, setScoresState] = useState<FetchState<ScoresResponse>>({
    status: 'idle',
  })
  const [timelineState, setTimelineState] = useState<
    FetchState<TimelineResponse>
  >({ status: 'idle' })
  const [passRatesState, setPassRatesState] = useState<
    FetchState<PassRatesResponse>
  >({ status: 'idle' })

  const token = localStorage.getItem(STORAGE_KEY) ?? ''

  useEffect(() => {
    if (!token || !selectedLab) return

    const fetchScores = fetch(`/analytics/scores?lab=${selectedLab}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json() as Promise<ScoresResponse>
    })

    const fetchTimeline = fetch(`/analytics/timeline?lab=${selectedLab}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json() as Promise<TimelineResponse>
    })

    const fetchPassRates = fetch(`/analytics/pass-rates?lab=${selectedLab}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json() as Promise<PassRatesResponse>
    })

    setScoresState({ status: 'loading' })
    setTimelineState({ status: 'loading' })
    setPassRatesState({ status: 'loading' })

    Promise.allSettled([fetchScores, fetchTimeline, fetchPassRates]).then(
      ([scoresResult, timelineResult, passRatesResult]) => {
        if (scoresResult.status === 'fulfilled') {
          setScoresState({ status: 'success', data: scoresResult.value })
        } else {
          setScoresState({
            status: 'error',
            message: scoresResult.reason.message,
          })
        }

        if (timelineResult.status === 'fulfilled') {
          setTimelineState({ status: 'success', data: timelineResult.value })
        } else {
          setTimelineState({
            status: 'error',
            message: timelineResult.reason.message,
          })
        }

        if (passRatesResult.status === 'fulfilled') {
          setPassRatesState({ status: 'success', data: passRatesResult.value })
        } else {
          setPassRatesState({
            status: 'error',
            message: passRatesResult.reason.message,
          })
        }
      },
    )
  }, [token, selectedLab])

  const scoresData =
    scoresState.status === 'success'
      ? {
          labels: scoresState.data.buckets.map((b) => b.bucket),
          datasets: [
            {
              label: 'Submissions',
              data: scoresState.data.buckets.map((b) => b.count),
              backgroundColor: 'rgba(54, 162, 235, 0.6)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 1,
            },
          ],
        }
      : { labels: [], datasets: [] }

  const timelineData =
    timelineState.status === 'success'
      ? {
          labels: timelineState.data.data.map((d) => d.date),
          datasets: [
            {
              label: 'Submissions per Day',
              data: timelineState.data.data.map((d) => d.submissions),
              borderColor: 'rgba(75, 192, 192, 1)',
              backgroundColor: 'rgba(75, 192, 192, 0.2)',
              tension: 0.1,
            },
          ],
        }
      : { labels: [], datasets: [] }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Dashboard</h1>
        <div className="lab-selector">
          <label htmlFor="lab-select">Select Lab: </label>
          <select
            id="lab-select"
            value={selectedLab}
            onChange={(e) => setSelectedLab(e.target.value)}
          >
            {LABS.map((lab) => (
              <option key={lab.id} value={lab.id}>
                {lab.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="charts-container">
        <div className="chart-card">
          <h2>Score Buckets</h2>
          {scoresState.status === 'loading' && <p>Loading...</p>}
          {scoresState.status === 'error' && (
            <p className="error">Error: {scoresState.message}</p>
          )}
          {scoresState.status === 'success' && (
            <Bar data={scoresData} options={{ responsive: true }} />
          )}
        </div>

        <div className="chart-card">
          <h2>Submissions Timeline</h2>
          {timelineState.status === 'loading' && <p>Loading...</p>}
          {timelineState.status === 'error' && (
            <p className="error">Error: {timelineState.message}</p>
          )}
          {timelineState.status === 'success' && (
            <Line data={timelineData} options={{ responsive: true }} />
          )}
        </div>
      </div>

      <div className="chart-card pass-rates-card">
        <h2>Pass Rates per Task</h2>
        {passRatesState.status === 'loading' && <p>Loading...</p>}
        {passRatesState.status === 'error' && (
          <p className="error">Error: {passRatesState.message}</p>
        )}
        {passRatesState.status === 'success' && (
          <table>
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Task Title</th>
                <th>Pass Rate</th>
                <th>Passed / Total</th>
              </tr>
            </thead>
            <tbody>
              {passRatesState.data.tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>{task.task_id}</td>
                  <td>{task.task_title}</td>
                  <td>{(task.pass_rate * 100).toFixed(1)}%</td>
                  <td>
                    {task.passed_submissions} / {task.total_submissions}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default Dashboard
