import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, FileText, CheckCircle2 } from 'lucide-react';
import { LANGS, STRINGS } from '../utils/translations';
import AdComponent from './AdComponent';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function CvUploader({
  lang,
  analysisEngine,
  customGeminiKey,
  onAnalysisSuccess
}) {
  const S = STRINGS[LANGS[lang].code];
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState("");
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const processFile = async (file) => {
    if (!file) return;
    if (file.type !== "application/pdf") {
      setError("Seuls les fichiers PDF sont supportés.");
      return;
    }

    setLoading(true);
    setError(null);
    setFileName(file.name);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("selected_model", analysisEngine);
    if (customGeminiKey) {
      formData.append("custom_gemini_key", customGeminiKey);
    }
    formData.append("lang_label", LANGS[lang].label);

    try {
      console.log("[CV_ANALYSIS] Uploading file:", file.name, "type:", file.type, "size:", file.size);
      console.log("[CV_ANALYSIS] selected_model:", analysisEngine);
      console.log("[CV_ANALYSIS] custom_gemini_key present:", !!customGeminiKey);
      
      const response = await fetch(`${API_BASE}/api/analyze-cv`, {
        method: "POST",
        body: formData,
      });

      const contentType = response.headers.get("content-type");
      const responseText = await response.text();
      
      console.log("[CV_ANALYSIS] Response status:", response.status);
      console.log("[CV_ANALYSIS] Response content-type:", contentType);
      console.log("[CV_ANALYSIS] Response text (first 300 chars):", responseText.substring(0, 300));
      
      if (!response.ok) {
        let errorMessage = `Erreur HTTP ${response.status}`;
        if (contentType && contentType.includes("application/json")) {
          try {
            const errorData = JSON.parse(responseText);
            errorMessage = errorData.detail || errorData.error || errorMessage;
          } catch (e) {
            console.error("[CV_ANALYSIS] Erreur lors du parsing de la réponse d'erreur:", e);
          }
        } else if (responseText.includes("<!doctype") || responseText.includes("<html")) {
          errorMessage = "Le backend n'est pas accessible. Vérifiez que le serveur est démarré sur " + API_BASE;
        }
        
        if (response.status === 400) {
          errorMessage += "\n\nCauses possibles :\n- Le fichier n'est pas un PDF\n- Le fichier est vide\n- Le PDF ne contient pas de texte extractible\n- Le texte extrait est trop court (< 50 caractères)";
        }
        
        console.error("[CV_ANALYSIS] Upload failed:", errorMessage);
        throw new Error(errorMessage);
      }

      if (!contentType || !contentType.includes("application/json")) {
        console.error("[CV_ANALYSIS] Invalid response type:", contentType);
        throw new Error("Le serveur a retourné une réponse invalide. Vérifiez que le backend est bien configuré.");
      }

      const data = JSON.parse(responseText);
      console.log("[CV_ANALYSIS] Success:", data);
      if (data.is_fallback) {
        console.warn("[CV_ANALYSIS] MODE SECOURS = Le parsing regex a été utilisé, pas l'IA");
      } else {
        console.info("[CV_ANALYSIS] MODE IA = L'analyse IA a réussi");
      }
      onAnalysisSuccess(data);
    } catch (err) {
      console.error("[CV_ANALYSIS] Unexpected error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const onButtonClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div
        className={`upload-card ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={onButtonClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          style={{ display: 'none' }}
          accept=".pdf"
          onChange={handleChange}
        />
        
        <div className="upload-icon">
          {loading ? (
            <div className="spinner" />
          ) : fileName ? (
            <CheckCircle2 size={32} style={{ color: 'var(--success-color)' }} />
          ) : (
            <Upload size={32} />
          )}
        </div>
        
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '700', marginBottom: '4px' }}>
            {fileName ? fileName : S.upload}
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {loading ? S.analyze : "Les fichiers PDF sont supportés jusqu'à 10MB"}
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div style={{ marginTop: '16px' }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(124,77,255,0.1), rgba(68,138,255,0.08))',
            border: '1px solid rgba(124,77,255,0.3)',
            padding: '16px',
            borderRadius: 'var(--radius-md)',
            marginBottom: '16px',
            textAlign: 'center',
            color: 'var(--text-primary)',
            fontWeight: '600',
            fontSize: '0.95rem'
          }}>
            ⏳ Analyse de votre CV en cours... (15-30 secondes)
          </div>
          <AdComponent />
        </div>
      )}

      {fileName && !loading && !error && (
        <div className="alert alert-success">
          <FileText size={18} />
          <span>{S.analyze_success}</span>
        </div>
      )}
    </div>
  );
}
