import { useState } from 'react'

type LoginProps = {
  onBack: () => void
  onLogin: () => void
}

const API_URL = 'http://127.0.0.1:8000'

function Login({ onBack, onLogin }: LoginProps) {
  const [isRegister, setIsRegister] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage('')
    setLoading(true)

    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login'

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          isRegister
            ? { name: name.trim(), email: email.trim().toLowerCase(), password }
            : { email: email.trim().toLowerCase(), password }
        ),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed. Please try again.')
      }

      if (isRegister) {
        setMessage('Account created! Please log in.')
        setIsRegister(false)
        setPassword('')
      } else {
        localStorage.setItem('infrascan_token', data.access_token)
        setMessage('Login successful!')
        onLogin()
      }
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Backend connection failed. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>InfraScan</h1>
        <p>AI-Powered Infrastructure Inspection</p>

        <h2>{isRegister ? 'Create an Account' : 'Welcome Back'}</h2>

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <label>
              Full Name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                placeholder="Enter your full name"
              />
            </label>
          )}

          <label>
            Email Address
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="Enter your email"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              placeholder="At least 8 characters"
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? 'Please wait...' : isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        {message && <p className="status-message">{message}</p>}

        <p>
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setIsRegister(!isRegister)
              setMessage('')
            }}
          >
            {isRegister ? 'Login' : 'Register'}
          </button>
        </p>

        <button type="button" className="back-button" onClick={onBack}>
          Back to Image Upload
        </button>
      </section>
    </main>
  )
}

export default Login