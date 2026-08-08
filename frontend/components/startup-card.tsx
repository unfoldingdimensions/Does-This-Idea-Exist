import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ExternalLink, FolderGit2, Star, ShieldCheck, Archive } from "lucide-react";
import type { Startup } from "@/lib/types";
import { foundedYear } from "@/lib/search";
import { cn } from "@/lib/utils";

function initials(name: string): string {
  return name
    .split(/[\s\-_/]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function StartupCard({
  startup,
  onVerified,
}: {
  startup: Startup;
  onVerified?: (s: Startup) => void;
}) {
  const dead = startup.status === "dead" || startup.status === "pivoted";
  const verified = startup.verified === 1;
  const year = foundedYear(startup.founded);

  return (
    <Card className={cn("flex h-full flex-col !rounded-xl", dead && "opacity-60")}>
      <CardContent className="flex h-full flex-col gap-2.5 p-3.5">
        <div className="flex items-center gap-2.5">
          <Avatar className="h-7 w-7 rounded-md bg-muted">
            <AvatarFallback className="rounded-md text-xs font-bold">
              {initials(startup.name)}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="truncate text-sm font-bold leading-tight">{startup.name}</span>
              {verified && (
                <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-primary" aria-label="Verified" />
              )}
            </div>
            {year && <p className="text-xs text-muted-foreground">founded {year}</p>}
          </div>
          {dead && (
            <Badge variant="secondary" className="gap-1 text-[11px]">
              <Archive className="h-3 w-3" /> Archived
            </Badge>
          )}
        </div>

        {startup.tagline && (
          <p className="text-[13px] font-medium leading-snug">{startup.tagline}</p>
        )}
        {startup.description && (
          <p className="line-clamp-3 text-[13px] leading-relaxed text-muted-foreground">
            {startup.description}
          </p>
        )}

        <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-1">
          {startup.category && <Badge variant="secondary" className="text-[11px]">{startup.category}</Badge>}
          {startup.language && <Badge variant="outline" className="text-[11px]">{startup.language}</Badge>}
          {typeof startup.stars === "number" && startup.stars > 0 && (
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Star className="h-3 w-3" /> {startup.stars.toLocaleString()}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 border-t pt-2.5">
          {startup.website_url && (
            <Button asChild variant="outline" size="sm" className="h-7 gap-1 text-xs">
              <a href={startup.website_url} target="_blank" rel="noreferrer">
                <ExternalLink className="h-3 w-3" /> Website
              </a>
            </Button>
          )}
          {startup.github_url && (
            <Button asChild variant="outline" size="sm" className="h-7 gap-1 text-xs">
              <a href={startup.github_url} target="_blank" rel="noreferrer">
                <FolderGit2 className="h-3 w-3" /> Code
              </a>
            </Button>
          )}
          <span className="ml-auto text-[11px] text-muted-foreground">
            {verified ? (
              "verified"
            ) : (
              <button
                type="button"
                onClick={() => onVerified?.(startup)}
                className="rounded text-[11px] font-medium text-primary hover:underline"
                title="Confirm this startup exists"
              >
                mark verified
              </button>
            )}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
