import { useState } from "react";
import { motion } from "framer-motion";
import { 
  Download, 
  FileText, 
  CheckCircle2,
  Loader2
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { loadLastResult } from "@/lib/api";

const reportSections = [
  { title: "Executive Summary", pages: 2, included: true },
  { title: "Architecture Overview", pages: 4, included: true },
  { title: "Component Analysis", pages: 8, included: true },
  { title: "Dependency Mapping", pages: 3, included: true },
  { title: "Risk Assessment", pages: 5, included: true },
  { title: "Recommendations", pages: 6, included: true },
  { title: "Evolution Roadmap", pages: 4, included: true },
  { title: "Technical Appendix", pages: 10, included: true },
];

export default function Reports() {
  const [isDownloading, setIsDownloading] = useState(false);
  const [showDownloadOptions, setShowDownloadOptions] = useState(false);
  const last = loadLastResult();

  const sanitizeReportContent = (raw: string): string => {
    if (!raw) return "";
    return raw
      // Remove Mermaid graph blocks
      .replace(/```mermaid[\s\S]*?```/gi, "")
      // Remove JSON output blocks
      .replace(/```json[\s\S]*?```/gi, "")
      // Remove excessive blank lines introduced after stripping blocks
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  };

  const buildReportMarkdown = (): string => {
    const detailedDoc = sanitizeReportContent(last?.report_document || "");
    if (detailedDoc) {
      return detailedDoc;
    }
    const safeAnalysis = sanitizeReportContent(last?.analysis_report || "No analysis report found.");
    const safePlan = sanitizeReportContent(last?.architecture_plan || "No architecture plan found.");
    return (
      `# Architecture Analysis Report\n\n` +
      `## Mode\n${last?.mode || "N/A"}\n\n` +
      (last?.warning ? `## Warning\n${last.warning}\n\n` : "") +
      `## Analysis Report\n${safeAnalysis}\n\n` +
      `## Architecture Plan\n${safePlan}\n`
    );
  };

  const downloadBlob = (content: BlobPart, mime: string, filename: string) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const toSimplePdfBytes = (text: string): Uint8Array => {
    const safe = text
      .replace(/\r/g, "")
      .split("\n")
      .map((line) =>
        line
          .replace(/\\/g, "\\\\")
          .replace(/\(/g, "\\(")
          .replace(/\)/g, "\\)")
          .slice(0, 110)
      );

    let y = 800;
    const lineHeight = 14;
    const streamLines = ["BT", "/F1 10 Tf"];
    for (const line of safe) {
      if (y < 50) break;
      streamLines.push(`1 0 0 1 50 ${y} Tm (${line || " "}) Tj`);
      y -= lineHeight;
    }
    streamLines.push("ET");
    const stream = streamLines.join("\n");
    const streamLen = stream.length;

    const objects: string[] = [];
    objects.push("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj");
    objects.push("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj");
    objects.push("3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj");
    objects.push("4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj");
    objects.push(`5 0 obj << /Length ${streamLen} >> stream\n${stream}\nendstream endobj`);

    let pdf = "%PDF-1.4\n";
    const offsets: number[] = [0];
    for (const obj of objects) {
      offsets.push(pdf.length);
      pdf += `${obj}\n`;
    }
    const xrefPos = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n`;
    pdf += "0000000000 65535 f \n";
    for (let i = 1; i < offsets.length; i++) {
      pdf += `${offsets[i].toString().padStart(10, "0")} 00000 n \n`;
    }
    pdf += `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefPos}\n%%EOF`;
    return new TextEncoder().encode(pdf);
  };

  const handleDownload = (format: "pdf" | "word" | "readme") => {
    setIsDownloading(true);
    setTimeout(() => {
      setIsDownloading(false);
      const reportMd = buildReportMarkdown();

      if (format === "readme") {
        downloadBlob(reportMd, "text/markdown;charset=utf-8", "architecture-report.md");
        return;
      }

      if (format === "word") {
        const bodyHtml = reportMd
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/\n/g, "<br/>");
        const docHtml = `<html><head><meta charset="utf-8"></head><body><h1>Architecture Analysis Report</h1><div>${bodyHtml}</div></body></html>`;
        downloadBlob(docHtml, "application/msword;charset=utf-8", "architecture-report.doc");
        return;
      }

      const pdfBytes = toSimplePdfBytes(reportMd);
      downloadBlob(new Blob([pdfBytes], { type: "application/pdf" }), "application/pdf", "architecture-report.pdf");
    }, 400);
  };

  const totalPages = reportSections.reduce((acc, section) => acc + section.pages, 0);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto">
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center mb-12"
            >
              <h1 className="text-3xl sm:text-4xl font-bold mb-4">
                <span className="text-foreground">Architecture </span>
                <span className="gradient-text">Report</span>
              </h1>
              <p className="text-muted-foreground">
                Download your comprehensive architecture analysis report
              </p>
            </motion.div>

            {/* Report Preview */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card p-8 mb-8"
            >
              {/* Document Header */}
              <div className="flex items-center justify-between pb-6 border-b border-border/50 mb-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent">
                    <FileText className="h-7 w-7 text-primary-foreground" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-foreground">
                      Architecture Analysis Report
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      Generated on {new Date().toLocaleDateString()} • {totalPages} pages
                    </p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-success/20 text-success">
                  Ready
                </span>
              </div>

              {/* Report Sections */}
              <div className="space-y-3 mb-8">
                <h3 className="text-sm font-medium text-muted-foreground mb-4">Report Contents</h3>
                {reportSections.map((section, index) => (
                  <motion.div
                    key={section.title}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + index * 0.05 }}
                    className="flex items-center justify-between p-3 rounded-lg bg-secondary/30"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      <span className="text-foreground">{section.title}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">{section.pages} pages</span>
                  </motion.div>
                ))}
              </div>

              {/* Download Button */}
              <Button
                variant="hero" 
                size="lg" 
                className="w-full"
                onClick={() => setShowDownloadOptions((v) => !v)}
                disabled={isDownloading}
              >
                {isDownloading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Preparing report...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-5 w-5" />
                    Download Report
                  </>
                )}
              </Button>
              {showDownloadOptions && (
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <Button variant="outline" onClick={() => handleDownload("pdf")} disabled={isDownloading}>
                    Download PDF
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload("word")} disabled={isDownloading}>
                    Download Word File
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload("readme")} disabled={isDownloading}>
                    Download readme file
                  </Button>
                </div>
              )}
            </motion.div>

            {/* Report Preview Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold text-foreground mb-4">Report Highlights</h3>
              
              <div className="prose prose-sm prose-invert max-w-none">
                <div className="p-4 rounded-lg bg-secondary/30 mb-4">
                  <h4 className="text-sm font-medium text-foreground mb-2">Executive Summary</h4>
                  <p className="text-sm text-muted-foreground">
                    This comprehensive analysis evaluated your software architecture across multiple 
                    dimensions including scalability, performance, maintainability, and security. 
                    Our AI agents identified key strengths in your current design while highlighting 
                    opportunities for improvement through strategic pattern adoption and infrastructure 
                    modernization.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-secondary/30 mb-4">
                  <h4 className="text-sm font-medium text-foreground mb-2">Key Findings</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Microservices architecture recommended for optimal scalability</li>
                    <li>Database layer identified as potential bottleneck at scale</li>
                    <li>Strong security posture with minor improvements suggested</li>
                    <li>6-month evolution roadmap provided for implementation</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg bg-secondary/30">
                  <h4 className="text-sm font-medium text-foreground mb-2">Next Steps</h4>
                  <p className="text-sm text-muted-foreground">
                    Review the detailed recommendations in Section 6 and begin with the high-priority 
                    items outlined in the Evolution Roadmap. Consider scheduling a technical review 
                    with your team to discuss implementation strategies.
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
