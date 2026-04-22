import { Route, Routes } from "react-router-dom";

function Placeholder({ title }: { title: string }) {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Server Provisioning Assistant</h1>
      <p style={{ color: "#555" }}>Scaffold live. {title}</p>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Placeholder title="Records list coming in Milestone 5." />} />
      <Route path="/records/:id" element={<Placeholder title="Record editor coming in Milestone 5." />} />
      <Route
        path="/records/:id/summary"
        element={<Placeholder title="Summary view coming in Milestone 5." />}
      />
    </Routes>
  );
}
