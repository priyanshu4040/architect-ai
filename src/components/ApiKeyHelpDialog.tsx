import { useState } from "react";
import { KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { validateApiKey } from "@/lib/api";
import {
  clearApiKeyErrorType,
  recordApiKeyErrorType,
} from "@/components/ApiKeyStatusBadge";
import {
  getUserFacingApiMessage,
  maskApiKey,
  type ApiErrorType,
} from "@/lib/apiErrors";
import { toast } from "sonner";

export function ApiKeyHelpDialog() {
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [testing, setTesting] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const handleTest = async () => {
    const clean = apiKey.trim();

    setTesting(true);
    setLastResult(null);

    try {
      const result = await validateApiKey(clean || undefined);

      if (result.valid) {
        clearApiKeyErrorType();

        const masked = result.masked_key || (clean ? maskApiKey(clean) : "env key");

        setLastResult(
          `Valid — Groq accepted key ${masked} (model: ${
            result.model || "llama-3.3-70b-versatile"
          }).`
        );

        toast.success("API key is valid");
      } else {
        const errType = (result.error_type || "PROVIDER_ERROR") as ApiErrorType;

        if (errType === "API_KEY_INVALID" || errType === "API_KEY_MISSING") {
          recordApiKeyErrorType(errType);
        } else {
          clearApiKeyErrorType();
        }

        setLastResult(result.message);
        toast.error(result.message);
      }
    } catch (e) {
      const msg = getUserFacingApiMessage(e);
      setLastResult(msg);
      toast.error(msg);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <KeyRound className="h-4 w-4" />
          API key
        </Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Groq API key</DialogTitle>
          <DialogDescription>
            This project uses <strong>Groq</strong> only, not OpenAI/Gemini keys.
            Keys are read from backend{" "}
            <code className="text-foreground">.env</code> by default — not stored
            in the browser.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-sm">
          <ol className="list-decimal pl-5 text-muted-foreground space-y-2">
            <li>
              In project root <code className="text-foreground">.env</code>, set{" "}
              <code className="text-foreground">GROQ_API_KEY=gsk_...</code> no
              quotes or spaces.
            </li>
            <li>Restart the FastAPI backend so it reloads environment variables.</li>
            <li>
              Use &quot;Test key&quot; below to verify with Groq. It uses .env if
              the field is empty.
            </li>
          </ol>

          <div>
            <Label htmlFor="groq-key-test">Test a key optional</Label>

            <Input
              id="groq-key-test"
              type="password"
              autoComplete="off"
              placeholder="Leave empty to test GROQ_API_KEY from .env"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="mt-2"
            />

            <p className="text-xs text-muted-foreground mt-1">
              Paste is only used for this test call — not saved in localStorage.
            </p>

            <Button
              className="mt-3 gap-2"
              variant="hero"
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Test key with Groq
            </Button>

            {lastResult ? (
              <p
                className={`mt-3 text-sm ${
                  lastResult.startsWith("Valid")
                    ? "text-emerald-600"
                    : "text-destructive"
                }`}
              >
                {lastResult}
              </p>
            ) : null}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}