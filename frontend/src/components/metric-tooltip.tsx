import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { glossary } from "@/lib/format";

export function MetricTooltip({ term, text }: { term?: string; text?: string }) {
  const content = text ?? (term ? glossary(term) : "");
  if (!content) return null;
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="What does this mean?"
            className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors"
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs leading-relaxed">{content}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
