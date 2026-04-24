import { Route, Routes } from "react-router-dom";
import { RecordEditor } from "@/components/RecordEditor";
import { RecordList } from "@/components/RecordList";
import { SummaryView } from "@/components/summary/SummaryView";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RecordList />} />
      <Route path="/records/:id" element={<RecordEditor />} />
      <Route path="/records/:id/summary" element={<SummaryView />} />
    </Routes>
  );
}
