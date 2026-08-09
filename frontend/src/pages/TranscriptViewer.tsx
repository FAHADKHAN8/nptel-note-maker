import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
export default function TranscriptViewer(){const {id}=useParams();const [t,setT]=useState<any>();const [text,setText]=useState("");useEffect(()=>{api.get(`/api/lectures/${id}/transcript`).then(r=>{setT(r.data);setText(r.data.cleaned_text)})},[id]);async function save(){const r=await api.put(`/api/lectures/${id}/transcript`,{cleaned_text:text});setT(r.data)}return <section><h2>Transcript</h2><p>{t?.source}</p><textarea value={text} onChange={e=>setText(e.target.value)} /><button onClick={save}>Save</button></section>}
