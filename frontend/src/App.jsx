import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setMessage("");
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select an image first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);

      const response = await fetch(
        "http://127.0.0.1:8000/api/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setMessage("Image uploaded successfully!");
    } catch (error) {
      setMessage(error.message || "Unable to connect to backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="navbar">
        <h2>InfraScan</h2>
        <span>AI-Powered Infrastructure Assessment</span>
      </header>

      <main className="container">
        <section className="welcome">
          <h1>Infrastructure Damage Assessment</h1>
          <p>
            Upload infrastructure images for crack and damage assessment.
          </p>
        </section>

        <section className="upload-card">
          <h2>Upload Infrastructure Image</h2>

          <input
            type="file"
            accept=".jpg,.jpeg,.png"
            onChange={handleFileChange}
          />

          {preview && (
            <div className="preview">
              <img src={preview} alt="Selected infrastructure" />
            </div>
          )}

          <button onClick={handleUpload} disabled={loading}>
            {loading ? "Uploading..." : "Upload Image"}
          </button>

          {message && <p className="message">{message}</p>}
        </section>
      </main>

      <footer>
        InfraScan | AI-Powered Crack & Damage Assessment
      </footer>
    </div>
  );
}

export default App;