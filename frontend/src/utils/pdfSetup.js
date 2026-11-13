import { pdfjs } from 'react-pdf';
// Vite must resolve the worker to a real URL — pdf.js defaults to bare "pdf.worker.mjs"
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

/** Always set — pdfjs ships a bare default that browsers reject. */
pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
