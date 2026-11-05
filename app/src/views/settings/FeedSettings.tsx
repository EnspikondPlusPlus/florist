import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { api, relTime, Source } from "../../api";
import { BRAND_NAME, Logo } from "../../components/Logo";
import { Button, cx, Spinner, toast } from "../../components/ui";
import { Card, SettingsTitle } from "./Settings";

type Kind = { kind: string; logo: string; label: string; fields: [string, string][]; presets?: { name: string; config: Record<string, string> }[] };
const KINDS: Kind[] = [
  { kind: "alphaxiv", logo: "alphaxiv", label: "alphaXiv", fields: [["interval", "7 Days"]] },
  { kind: "hf_papers", logo: "huggingface", label: "Hugging Face papers", fields: [] },
  { kind: "arxiv", logo: "arxiv", label: "arXiv", fields: [["category", "cs.LG"]], presets: [{ name: "arXiv cs.CL", config: { category: "cs.CL" } }, { name: "arXiv cs.CV", config: { category: "cs.CV" } }, { name: "arXiv cs.RO", config: { category: "cs.RO" } }] },
  { kind: "github", logo: "github", label: "GitHub", fields: [["topic", "llm"], ["repo", "owner/name"]] },
  { kind: "hn", logo: "hn", label: "Hacker News", fields: [["query", "LLM"]] },
  { kind: "reddit", logo: "reddit", label: "Reddit", fields: [["subreddit", "MachineLearning"]], presets: [{ name: "r/MachineLearning", config: { subreddit: "MachineLearning" } }, { name: "r/LocalLLaMA", config: { subreddit: "LocalLLaMA" } }] },
  { kind: "youtube", logo: "youtube", label: "YouTube", fields: [["channel_id", "UC…"]], presets: [{ name: "Andrej Karpathy", config: { channel_id: "UCXUPKJO5MZQN11PqgIvyuvQ" } }, { name: "Yannic Kilcher", config: { channel_id: "UCZHmQk67mSJgfCCTn7xBfew" } }] },
  { kind: "bluesky", logo: "bluesky", label: "Bluesky", fields: [["handle", "name.bsky.social"]] },
  { kind: "mastodon", logo: "mastodon", label: "Mastodon", fields: [["account", "@user@instance.social"]] },
  { kind: "lobsters", logo: "lobsters", label: "Lobsters", fields: [["tag", "ai"]] },
  { kind: "rss", logo: "rss", label: "RSS / blog / podcast", fields: [["url", "https://…/feed"]], presets: [{ name: "Hugging Face blog", config: { url: "https://huggingface.co/blog/feed.xml" } }, { name: "Lil'Log", config: { url: "https://lilianweng.github.io/index.xml" } }, { name: "Simon Willison", config: { url: "https://simonwillison.net/atom/everything/" } }] },
  { kind: "email", logo: "email", label: "Newsletters", fields: [["folder", "Florist"], ["path", "or a local mail folder"]] },
  { kind: "folder", logo: "folder", label: "Notes folder", fields: [["path", "C:/Users/me/Notes/inbox"]] },
];

const SHORT: Record<string, string> = { hf_papers: "HF papers", hn: "HN", rss: "RSS", email: "Mail", folder: "Notes" };

function endpoint(s: Source): string {
  const c = s.config;
  return ({
    alphaxiv: "https://www.alphaxiv.org/", hf_papers: "https://huggingface.co/papers", arxiv: c.category ? `https://arxiv.org/list/${c.category}/recent` : "https://arxiv.org",
    github: c.repo ? `https://github.com/${c.repo}/releases` : `https://github.com/topics/${c.topic ?? ""}`, hn: `https://hn.algolia.com/?q=${encodeURIComponent(c.query ?? "")}`,
    reddit: `https://www.reddit.com/r/${c.subreddit}`, youtube: `https://www.youtube.com/channel/${c.channel_id}`, bluesky: `https://bsky.app/profile/${c.handle}`,
    lobsters: `https://lobste.rs/t/${c.tag}`, rss: c.url, mastodon: "",
  } as Record<string, string>)[s.kind] ?? "";
}

export default function FeedSettings() {
  const qc = useQueryClient();
  const src = useQuery({ queryKey: ["sources"], queryFn: () => api.get<Source[]>("/api/sources") });
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api.get<any>("/api/settings") });
  const refresh = () => qc.invalidateQueries({ queryKey: ["sources"] });
  const add = useMutation({ mutationFn: (b: any) => api.post("/api/sources", b), onSuccess: () => { refresh(); toast("Source added"); } });
  const del = useMutation({ mutationFn: (id: string) => api.del(`/api/sources/${id}`), onSuccess: refresh });
  const toggle = useMutation({ mutationFn: (s: Source) => api.post("/api/sources", { ...s, enabled: !s.enabled }), onSuccess: refresh });
  const pull = useMutation({ mutationFn: (id?: string) => api.post("/api/feed/fetch", { source_id: id, force: true }), onSuccess: () => { toast("Pulling…"); setTimeout(refresh, 4000); } });
  const put = useMutation({ mutationFn: (p: any) => api.put("/api/settings", p), onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }) });
  const [kind, setKind] = useState<Kind>(KINDS[10]);
  const [cfg, setCfg] = useState<Record<string, string>>({});
  if (!src.data) return <Spinner />;

  return (
    <>
      <SettingsTitle title="Feed" sub="Where inspiration comes from. Everything lands in one ranked stream." />
      <Card title="Sources" right={<Button size="sm" busy={pull.isPending} onClick={() => pull.mutate(undefined)}><RefreshCw size={12} />Pull all</Button>}>
        <div className="-mx-5 -my-4 divide-y divide-border-soft">
          {src.data.map((s) => {
            const url = endpoint(s);
            return (
              <div key={s.id} className={cx("flex items-center gap-3 px-5 py-2.5", !s.enabled && "opacity-55")}>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface"><Logo id={s.kind === "hn" ? "hn" : s.kind} size={17} /></span>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium">{s.name}</div>
                  <div className="truncate text-[11.5px] text-subtext">
                    {url ? <a href={url} target="_blank" rel="noreferrer" className="hover:underline">{url.replace(/^https?:\/\//, "")}</a> : Object.values(s.config).join(" · ")}
                    {s.last_error && <span className="text-red"> · {s.last_error.slice(0, 60)}</span>}
                  </div>
                </div>
                <span className="w-20 text-right text-[11.5px] text-muted">{s.last_fetched ? relTime(s.last_fetched) : "never"}</span>
                <button title="Pull now" onClick={() => pull.mutate(s.id)} className="rounded-md p-1.5 text-subtext hover:bg-hover"><RefreshCw size={13} /></button>
                <label className="relative inline-flex cursor-pointer items-center" title={s.enabled ? "Active" : "Paused"}>
                  <input type="checkbox" checked={s.enabled} onChange={() => toggle.mutate(s)} className="peer sr-only" />
                  <span className="h-5 w-9 rounded-full bg-border transition peer-checked:bg-leaf" />
                  <span className="absolute left-0.5 h-4 w-4 rounded-full bg-white shadow transition peer-checked:translate-x-4" />
                </label>
                <button title="Remove" onClick={() => del.mutate(s.id)} className="rounded-md p-1.5 text-muted hover:text-red"><Trash2 size={13} /></button>
              </div>
            );
          })}
        </div>
      </Card>

      <Card title="Add a source" icon={<Plus size={15} />}>
        <div className="mb-4 grid grid-cols-7 gap-1.5">
          {KINDS.map((k) => (
            <button key={k.kind} title={k.label} onClick={() => { setKind(k); setCfg({}); }}
              className={cx("flex flex-col items-center gap-1 rounded-lg border px-1 py-2 text-[10.5px]", kind.kind === k.kind ? "border-leaf bg-leaf-soft/40" : "border-border-soft hover:border-border")}>
              <Logo id={k.logo} size={18} /><span className="w-full truncate text-center text-subtext">{SHORT[k.kind] ?? k.label}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-end gap-2">
          {kind.fields.map(([f, ph]) => (
            <label key={f} className="min-w-[180px] flex-1 text-[12px]"><div className="mb-1 capitalize text-subtext">{f.replace("_", " ")}</div>
              <input className="h-8 w-full text-[12.5px]" placeholder={ph} value={cfg[f] ?? ""} onChange={(e) => setCfg({ ...cfg, [f]: e.target.value })} /></label>
          ))}
          <Button kind="primary" onClick={() => add.mutate({ kind: kind.kind, name: cfg[kind.fields[0]?.[0]] ? `${kind.label}: ${cfg[kind.fields[0][0]]}` : kind.label,
            config: Object.fromEntries(Object.entries(cfg).filter(([, v]) => v)) })}>Add {BRAND_NAME[kind.kind] ?? kind.label}</Button>
        </div>
        {kind.presets && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[12px]">
            <span className="text-muted">Quick add:</span>
            {kind.presets.map((p) => <button key={p.name} onClick={() => add.mutate({ kind: kind.kind, name: p.name, config: p.config })}
              className="flex items-center gap-1 rounded-full border border-border-soft px-2.5 py-0.5 hover:border-leaf"><Logo id={kind.logo} size={11} />{p.name}</button>)}
          </div>
        )}
      </Card>

      <Card title="Other">
        <div className="flex flex-wrap items-center gap-6 text-[13px]">
          <label className="flex items-center gap-2"><input type="checkbox" checked={!!settings.data?.auto_fetch_feed} onChange={(e) => put.mutate({ auto_fetch_feed: e.target.checked })} className="accent-[var(--leaf)]" />Pull sources in the background</label>
          <span className="flex items-center gap-2 text-subtext">Save anything else:
            <a href={`javascript:(()=>{fetch('${location.origin}/api/share?url='+encodeURIComponent(location.href)+'&note='+encodeURIComponent(getSelection().toString()),{mode:'no-cors'});alert('Saved to Florist')})()`}
              className="rounded-md border border-leaf bg-leaf-soft px-2.5 py-1 text-[12.5px] font-medium text-leaf-ink no-underline" title="Drag to your bookmarks bar">🌱 Save to Florist</a>
            <span className="text-[11.5px] text-muted">drag to your bookmarks bar</span></span>
        </div>
      </Card>
    </>
  );
}
