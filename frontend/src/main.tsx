import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { BookOpen, Plus } from "lucide-react";
import "./style.css";
import Dashboard from "./pages/Dashboard";
import ImportCourse from "./pages/ImportCourse";
import CourseDetails from "./pages/CourseDetails";
import TranscriptViewer from "./pages/TranscriptViewer";
import NotesEditor from "./pages/NotesEditor";

function App() {
  return <BrowserRouter><div className="shell"><aside><h1><BookOpen size={22}/>NPTEL AI Notes</h1><Link to="/"><BookOpen size={16}/>Dashboard</Link><Link to="/import"><Plus size={16}/>Import</Link></aside><main><Routes><Route path="/" element={<Dashboard/>}/><Route path="/import" element={<ImportCourse/>}/><Route path="/courses/:id" element={<CourseDetails/>}/><Route path="/lectures/:id/transcript" element={<TranscriptViewer/>}/><Route path="/lectures/:id/notes" element={<NotesEditor/>}/></Routes></main></div></BrowserRouter>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
