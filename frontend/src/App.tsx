
import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [message, setMessage] = useState("Connecting to backend...");
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [crackPercentage, setCrackPercentage] = useState<number | null>(null);
  const [mask, setMask] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/")
      .then((response) => {
        if (!response.ok) throw new Error("Backend request failed");
        return response.json();
      })
      .then((data) => setMessage(data.message))
      .catch(() => setMessage("Backend connection failed"));
  }, []);

  const handleImageChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (file) {
      setSelectedImage(file);
      setPreview(URL.createObjectURL(file));
      setCrackPercentage(null);
      setMask(null);
      setError("");
    }
  };

  const analyzeImage = async () => {
    if (!selectedImage) {
      setError("Please select an image first.");
      return;
    }

    setLoading(true);
    setError("");
    setCrackPercentage(null);
    setMask(null);

    const formData = new FormData();
    formData.append("file", selectedImage);

    try {
      const response = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Prediction failed");
      }

      setCrackPercentage(data.crack_percentage);
      setMask(data.mask);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to analyze image"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-container">
      <h1>InfraScan</h1>
      <h2>AI-Powered Crack & Damage Assessment</h2>

      <p>
        Backend status: <strong>{message}</strong>
      </p>

      <section className="upload-section">
        <h2>Upload Infrastructure Image</h2>
        <p>Select an image of a road, wall, or concrete surface.</p>

        <input
          type="file"
          accept="image/*"
          onChange={handleImageChange}
        />

        {preview && (
          <div className="preview-section">
            <h3>Original Image</h3>
            <img src={preview} alt="Selected infrastructure" className="image-preview" />
            <p>{selectedImage?.name}</p>

            <button onClick={analyzeImage} disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Image"}
            </button>
          </div>
        )}

        {error && <p className="error-message">{error}</p>}

        {crackPercentage !== null && mask && (
          <div className="result-section">
            <h2>Analysis Results</h2>
            <h3>Crack Percentage: {crackPercentage}%</h3>

            <h3>Detected Crack Mask</h3>
            <img
              src={`data:image/png;base64,${mask}`}
              alt="Predicted crack mask"
              className="image-preview"
            />
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
