// A chapter's number and name, above its heading. The home page's chapters are a
// real sequence (one attack, the gap, the scan, the proof, the result, the people).
export default function Chapter({ n, children }) {
  return (
    <div className="caption mb-6 flex items-center gap-3">
      <span className="grid h-7 min-w-9 place-items-center rounded-[3px] border-[1.5px] border-current px-1.5 tabular-nums">{n}</span>
      <span>{children}</span>
    </div>
  )
}
