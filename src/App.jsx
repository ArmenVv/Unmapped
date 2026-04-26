import "./style.css"
import { useState } from "react"

export default function App() {
  const [mode, setMode] = useState(null)
  const [jobType, setJobType] = useState("")
  const [hireText, setHireText] = useState("")
  const [file, setFile] = useState(null)
  const [jobSubmitted, setJobSubmitted] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const [hireResults, setHireResults] = useState(null)

  if (mode === "job") {
    if (jobSubmitted) {
      return (
        <div className="background">
          <div className="blob blob1"></div>
          <div className="blob blob2"></div>
          <div className="blob blob3"></div>

          <div className="job-page">
            <div className="job-form page-animate success-box">
              <h1>Application Sent</h1>
              <p>
                Your data was sent successfully.
                You will receive an email if someone wants to reach you.
              </p>

              <button
                className="continue-btn"
                onClick={() => {
                  setJobSubmitted(false)
                  setMode(null)
                }}
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="background">
        <div className="blob blob1"></div>
        <div className="blob blob2"></div>
        <div className="blob blob3"></div>

        <div className="job-page">
          <form
            className="job-form page-animate"
            onSubmit={(e) => {
              e.preventDefault()
              setJobSubmitted(true)
            }}
          >
            <button
              type="button"
              className="back-btn"
              onClick={() => setMode(null)}
            >
              ← Back
            </button>

            <h1>Find Your Job</h1>
            <p>Tell us what kind of job you want.</p>

            <textarea
              className="job-input"
              value={jobType}
              onChange={(e) => setJobType(e.target.value)}
              placeholder="Example: frontend developer, AI engineer..."
              required
            />

            <input className="job-input" placeholder="First name" required />
            <input className="job-input" placeholder="Last name" required />

            <input
              className="job-input"
              type="number"
              min="18"
              placeholder="Age"
              required
            />

            <input
              className="job-input"
              type="tel"
              placeholder="Phone number"
              required
            />

            <input
              className="job-input"
              type="email"
              placeholder="Email"
              required
            />

            <div className="upload-container">
              <label className="upload-box">
                <div className="upload-content">
                  <span>Upload CV</span>
                  <br />
                  <small>PDF / DOC / DOCX</small>
                </div>

                <input type="file" accept=".pdf,.doc,.docx" required />
              </label>

              <label className="upload-box">
                <div className="upload-content">
                  <span>💾 Upload ChatGPT History</span>
                  <br />
                  <small>JSON file only</small>
                </div>

                <input
                  type="file"
                  accept=".json,application/json"
                  required
                  onChange={(e) => setFile(e.target.files[0])}
                />
              </label>
            </div>

            {file && <p className="file-name">Uploaded: {file.name}</p>}

            <button className="continue-btn" type="submit">
              Continue
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (mode === "hire") {
    if (selectedCandidate) {
      return (
        <div className="background">
          <div className="blob blob1"></div>
          <div className="blob blob2"></div>
          <div className="blob blob3"></div>

          <div className="job-page">
            <div className="job-form page-animate">
              <button
                className="back-btn"
                onClick={() => setSelectedCandidate(null)}
              >
                ← Back
              </button>

              <div className="candidate-header">
                <div>
                  <h1>{selectedCandidate.name}</h1>
                  <p><b>Role:</b> {selectedCandidate.role}</p>
                  <p><b>Email:</b> {selectedCandidate.email}</p>
                  <p><b>Phone:</b> {selectedCandidate.phone}</p>
                  <p><b>Age:</b> {selectedCandidate.age}</p>
                  <p><b>Experience:</b> {selectedCandidate.experience}</p>
                  <p><b>Skills:</b> {selectedCandidate.skills}</p>
                </div>

                <div className="candidate-rating">
                  <h1>{selectedCandidate.rating}</h1>
                  <span>Rating</span>
                </div>
              </div>

              <div className="candidate-description">
                <h3>Description</h3>
                <p>{selectedCandidate.description}</p>
              </div>

              <a
                className="email-btn"
                href={`mailto:${selectedCandidate.email}`}
              >
                Email candidate
              </a>
            </div>
          </div>
        </div>
      )
    }

    if (hireResults) {
      return (
        <div className="background">
          <div className="blob blob1"></div>
          <div className="blob blob2"></div>
          <div className="blob blob3"></div>

          <div className="job-page">
            <div className="job-form page-animate">
              <button
                className="back-btn"
                onClick={() => {
                  setHireResults(null)
                  setSelectedCandidate(null)
                  setMode(null)
                }}
              >
                ← Back
              </button>

              <h1>Matching Candidates</h1>

              <input
                className="job-input"
                type="text"
                value={hireText}
                onChange={(e) => setHireText(e.target.value)}
                placeholder="Search candidates..."
              />

              <div className="candidate-list">
                {hireResults.map((person, index) => (
                  <div
                    className="candidate-card"
                    key={index}
                    onClick={() => setSelectedCandidate(person)}
                  >
                    <div className="info-container">
                      <h3>{person.name}</h3>
                      <p>{person.role}</p>
                      <span>{person.email}</span>
                    </div>

                    <h1>{person.rating}</h1>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="background">
        <div className="blob blob1"></div>
        <div className="blob blob2"></div>
        <div className="blob blob3"></div>

        <div className="job-page">
          <form
            className="job-form page-animate"
            onSubmit={(e) => {
              e.preventDefault()

              setHireResults([
                {
                  name: "Armen Vardanyan",
                  role: "Frontend Developer",
                  email: "armen@example.com",
                  phone: "+374 99 123456",
                  age: 22,
                  experience: "2 years",
                  skills: "React, JavaScript, CSS",
                  description: "Interested in frontend jobs and startup projects.",
                  rating: 4.7,
                },
                {
                  name: "David Hakobyan",
                  role: "React Developer",
                  email: "david@example.com",
                  phone: "+374 98 654321",
                  age: 24,
                  experience: "3 years",
                  skills: "React, Next.js, TypeScript",
                  description: "Looking for remote frontend roles.",
                  rating: 9.2,
                },
              ].sort((a, b) => b.rating - a.rating))
            }}
          >
            <button
              type="button"
              className="back-btn"
              onClick={() => setMode(null)}
            >
              ← Back
            </button>

            <h1>Hire Employees</h1>
            <p>Describe what kind of employee you need.</p>

            <textarea
              className="job-input"
              value={hireText}
              onChange={(e) => setHireText(e.target.value)}
              placeholder="Example: Need a frontend developer with React experience for startup project..."
              required
            />

            <button className="continue-btn" type="submit">
              Continue
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="background">
      <div className="blob blob1"></div>
      <div className="blob blob2"></div>
      <div className="blob blob3"></div>

      <div className="content page-animate">
        <h1>UNMAPPED</h1>
        <p className="subtitle">Choose how you want to continue</p>

        <div className="choice-cards">
          <button
            className="choice-card"
            onClick={() => {
              setJobSubmitted(false)
              setMode("job")
            }}
          >
            <span className="icon">💼</span>
            <span className="title">I’m finding a job</span>
            <span className="desc">Search jobs and build your profile</span>
          </button>

          <button
            className="choice-card"
            onClick={() => {
              setHireResults(null)
              setSelectedCandidate(null)
              setMode("hire")
            }}
          >
            <span className="icon">🏢</span>
            <span className="title">I’m hiring employees</span>
            <span className="desc">Find candidates and post openings</span>
          </button>
        </div>
      </div>
    </div>
  )
}