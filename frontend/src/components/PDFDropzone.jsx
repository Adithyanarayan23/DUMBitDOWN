import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, Upload, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import glassStyles from '../styles/glass.module.css';

/**
 * PDFDropzone — single upload that hands off to Document Mode.
 * States: idle → uploading → error (success opens DocumentMode via callback)
 */
function PDFDropzone({ onDocumentReady }) {
  const [state, setState] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileName, setFileName] = useState('');

  const MAX_SIZE = 50 * 1024 * 1024;

  const onDrop = useCallback(
    async (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        const rejected = rejectedFiles[0];
        setState('error');
        setErrorMessage(
          rejected.file.size > MAX_SIZE
            ? 'File too large. Maximum size is 50MB.'
            : 'Only PDF files are accepted.'
        );
        return;
      }
      if (acceptedFiles.length === 0) return;

      const selectedFile = acceptedFiles[0];
      setFileName(selectedFile.name);
      setState('uploading');
      setUploadProgress(0);

      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => (prev >= 90 ? 90 : prev + 10));
      }, 200);

      try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch('/api/upload/pdf', {
          method: 'POST',
          body: formData,
        });

        clearInterval(progressInterval);
        setUploadProgress(100);

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || 'Upload failed');
        }

        const manifest = await response.json();
        setState('idle');
        setUploadProgress(0);
        onDocumentReady?.({ manifest, file: selectedFile });
      } catch (err) {
        clearInterval(progressInterval);
        setState('error');
        setErrorMessage(err.message || 'Upload failed. Please try again.');
      }
    },
    [onDocumentReady]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: MAX_SIZE,
    noClick: state === 'uploading',
    noKeyboard: state === 'uploading',
  });

  const handleReset = () => {
    setState('idle');
    setErrorMessage('');
    setUploadProgress(0);
    setFileName('');
  };

  return (
    <div className="pdf-dropzone">
      <AnimatePresence mode="wait">
        {(state === 'idle' || state === 'error') && (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            {...getRootProps()}
            className={`dropzone-area ${state === 'error' ? 'dropzone-error' : ''} ${
              isDragActive ? 'dropzone-active' : ''
            }`}
          >
            <input {...getInputProps()} />
            <div className="dropzone-content">
              {state === 'error' ? (
                <>
                  <AlertCircle size={40} className="dropzone-icon error" />
                  <p className="dropzone-text error">{errorMessage}</p>
                  <button
                    className={glassStyles.textButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleReset();
                    }}
                  >
                    Try Again
                  </button>
                </>
              ) : isDragActive ? (
                <>
                  <Upload size={40} className="dropzone-icon active" />
                  <p className="dropzone-text">Drop the PDF here...</p>
                </>
              ) : (
                <>
                  <FileText size={28} className="dropzone-icon" />
                  <p className="dropzone-text">Drop a PDF or click to upload</p>
                  <p className="dropzone-hint">
                    Opens an interactive reader — select text, tables, or figures
                  </p>
                </>
              )}
            </div>
          </motion.div>
        )}

        {state === 'uploading' && (
          <motion.div
            key="uploading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={`upload-state ${glassStyles.stitchedGlass}`}
          >
            <div className="upload-info">
              <FileText size={24} />
              <span className="filename">{fileName}</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ transform: `scaleX(${uploadProgress / 100})` }}
              />
            </div>
            <p className="upload-status">Opening PDF…</p>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .pdf-dropzone { margin-top: var(--space-md); }
        .dropzone-area {
          border: 2px dashed var(--glass-border);
          border-radius: var(--radius-lg);
          padding: var(--space-lg);
          cursor: pointer;
          transition: border-color var(--transition-normal), background-color var(--transition-normal);
          background: var(--glass-bg);
        }
        .dropzone-area:hover {
          border-color: var(--color-gold);
          background: var(--glass-bg-heavy);
        }
        .dropzone-active {
          border-color: var(--color-amber);
          background: var(--color-amber-tint);
        }
        .dropzone-error {
          border-color: var(--color-maroon);
          background: var(--color-maroon-tint);
        }
        .dropzone-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--space-md);
          text-align: center;
        }
        .dropzone-icon { color: var(--color-parchment-3); }
        .dropzone-icon.active { color: var(--color-amber); }
        .dropzone-icon.error { color: var(--color-error); }
        .dropzone-text {
          font-family: var(--font-body);
          font-size: var(--t-body);
          color: var(--color-parchment);
        }
        .dropzone-hint {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-3);
        }
        .upload-state { padding: var(--space-lg); }
        .upload-info {
          display: flex;
          align-items: center;
          gap: var(--space-md);
          margin-bottom: var(--space-md);
        }
        .filename {
          font-family: var(--font-body);
          font-size: var(--t-body);
          color: var(--color-parchment);
          word-break: break-all;
        }
        .progress-bar {
          width: 100%;
          height: 4px;
          background: var(--glass-border);
          border-radius: 2px;
          overflow: hidden;
          margin-bottom: var(--space-sm);
        }
        .progress-fill {
          height: 100%;
          width: 100%;
          background: var(--color-amber);
          border-radius: 2px;
          transform: scaleX(0);
          transform-origin: left center;
          transition: transform 0.2s ease;
        }
        .upload-status {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
          text-align: center;
        }
      `}</style>
    </div>
  );
}

export default PDFDropzone;
