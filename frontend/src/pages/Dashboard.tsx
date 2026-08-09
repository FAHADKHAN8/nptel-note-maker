import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
export default function Dashboard(){const [courses,setCourses]=useState<any[]>([]);useEffect(()=>{api.get("/api/courses").then(r=>setCourses(r.data))},[]);return <section><h2>Dashboard</h2><div className="grid">{courses.map(c=><article className="card" key={c.id}><h3>{c.title}</h3><p>{c.total_lectures} lectures · {c.status}</p><Link className="button" to={`/courses/${c.id}`}>Continue</Link></article>)}</div></section>}
