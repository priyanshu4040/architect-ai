import DOMPurify from "dompurify";
import { marked } from "marked";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

const REPORT_STYLES = `
  .report-root { font-family: Calibri, "Segoe UI", "Helvetica Neue", Arial, sans-serif; line-height: 1.45; color: #1a1a1a; background: #fff; }
  .report-root { max-width: 820px; margin: 0 auto; padding: 28px 32px 48px; box-sizing: border-box; }
  .report-root h1 { font-size: 22pt; font-weight: 700; border-bottom: 2px solid #e5e5e5; padding-bottom: 10px; margin-top: 0; }
  .report-root h2 { font-size: 15pt; font-weight: 600; margin: 1.35em 0 0.5em; border-bottom: 1px solid #eee; padding-bottom: 6px; }
  .report-root h3 { font-size: 12pt; font-weight: 600; margin: 1.1em 0 0.4em; }
  .report-root p { margin: 0.55em 0; word-wrap: break-word; }
  .report-root ul, .report-root ol { margin: 0.45em 0 0.45em 1.25em; }
  .report-root li { margin: 0.2em 0; }
  .report-root table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 9.5pt; page-break-inside: avoid; }
  .report-root th, .report-root td { border: 1px solid #bbb; padding: 6px 10px; text-align: left; vertical-align: top; }
  .report-root th { background: #f4f4f4; font-weight: 600; }
  .report-root tr:nth-child(even) td { background: #fafafa; }
  .report-root pre { background: #f6f8fa; border: 1px solid #ddd; border-radius: 4px; padding: 12px; overflow-x: auto; font-size: 8.5pt; white-space: pre-wrap; word-break: break-word; margin: 12px 0; }
  .report-root code { font-family: Consolas, "Cascadia Mono", "Courier New", monospace; font-size: 0.92em; }
  .report-root pre code { font-size: inherit; }
  .report-root blockquote { border-left: 4px solid #ccc; margin: 1em 0; padding: 4px 0 4px 14px; color: #444; }
  .report-root hr { border: none; border-top: 1px solid #ddd; margin: 24px 0; }
  .report-root strong { font-weight: 600; }
`;

function escapeHtmlAttr(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function markdownToSanitizedHtmlFragment(markdown: string): string {
  const raw = marked.parse(markdown, { async: false }) as string;
  return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } });
}

/** Full HTML document suitable for “Save as Word” (.doc) with structured headings, tables, and code blocks. */
export function buildReportWordDocumentHtml(title: string, markdown: string): string {
  const body = markdownToSanitizedHtmlFragment(markdown);
  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtmlAttr(title)}</title>
  <!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
  <style type="text/css">${REPORT_STYLES}</style>
</head>
<body>
  <div class="report-root">${body}</div>
</body>
</html>`;
}

/**
 * Rasterizes the same HTML used for Word into a multi-page A4 PDF (matches readme content structure).
 */
export async function markdownToPdfBlob(markdown: string): Promise<Blob> {
  const body = markdownToSanitizedHtmlFragment(markdown);
  const host = document.createElement("div");
  host.className = "report-root";
  host.style.cssText =
    "position:fixed;left:-14000px;top:0;width:794px;background:#fff;z-index:-1;pointer-events:none;";
  host.innerHTML = body;

  const styleEl = document.createElement("style");
  styleEl.textContent = REPORT_STYLES;

  document.body.appendChild(styleEl);
  document.body.appendChild(host);

  try {
    if (document.fonts?.ready) {
      await document.fonts.ready.catch(() => undefined);
    }
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));

    const scale = Math.min(2, Math.max(1, (window.devicePixelRatio || 1) * 1.25));
    const canvas = await html2canvas(host, {
      scale,
      useCORS: true,
      logging: false,
      backgroundColor: "#ffffff",
      windowWidth: host.scrollWidth,
      windowHeight: host.scrollHeight,
    });

    const imgData = canvas.toDataURL("image/png", 1.0);
    const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const imgWidth = pageWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = 0;

    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    while (heightLeft > 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    return pdf.output("blob");
  } finally {
    host.remove();
    styleEl.remove();
  }
}
