import { AlertCircle, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { API_KEY_USER_MESSAGE } from "@/lib/apiErrors";

type Props = {
  message?: string;
  title?: string;
  onDismiss?: () => void;
  className?: string;
};

export function ApiErrorAlert({
  message = API_KEY_USER_MESSAGE,
  title = "API key issue",
  onDismiss,
  className,
}: Props) {
  return (
    <Alert variant="destructive" className={cn(className)}>
      <AlertCircle className="h-4 w-4" />
      <div className="flex w-full items-start justify-between gap-2">
        <div>
          <AlertTitle>{title}</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </div>
        {onDismiss ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0 text-destructive hover:text-destructive"
            onClick={onDismiss}
            aria-label="Dismiss alert"
          >
            <X className="h-4 w-4" />
          </Button>
        ) : null}
      </div>
    </Alert>
  );
}
