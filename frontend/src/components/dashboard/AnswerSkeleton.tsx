import Card from '../ui/Card';

export default function AnswerSkeleton() {
  return (
    <Card className="mt-4 animate-pulse" >
      <div aria-label="Loading answer">
        <div className="h-6 w-2/3 rounded-lg bg-ink-800" />
        <div className="mt-3 space-y-2">
          <div className="h-4 w-full rounded-lg bg-ink-850" />
          <div className="h-4 w-5/6 rounded-lg bg-ink-850" />
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-28 rounded-lg bg-ink-850" />
          ))}
        </div>
      </div>
    </Card>
  );
}
