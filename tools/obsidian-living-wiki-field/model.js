'use strict';

// Disposable projection of the archive. Never edits records or makes evidence decisions.
const NOTE_TYPES = ['RNO', 'MNO', 'FO', 'NameO', 'RefO', 'RelO'];
const list = v => v == null ? [] : Array.isArray(v) ? v : [v];
const meta = (app, file) => (app.metadataCache.getFileCache(file) || {}).frontmatter || {};
function typeOf(app, file) {
  const fm = meta(app, file), t = String(fm.type || '').toLowerCase();
  if (NOTE_TYPES.includes(fm.type)) return fm.type;
  if (['source', 'source-record', 'reference', 'ref'].includes(t)) return 'RefO';
  if (['relation', 'relation-object'].includes(t)) return 'RelO';
  if (['object', 'field'].includes(t)) return 'FO';
  if (t === 'name') return 'NameO';
  if (['mapping', 'index', 'claim-object', 'succession-record', 'event', 'lineage'].includes(t)) return 'MNO';
  return 'RNO';
}
function buildModel(app) {
  const nodes = [], byPath = Object.create(null), byRecord = Object.create(null);
  const duplicates = new Set(), relations = Object.create(null), unresolved = [];
  const files = app.vault.getMarkdownFiles().filter(f => !/^(?:tools|scripts|\.maws|\.claude|openspec|_audits|_exports|_search|_originals)\//.test(f.path))
    .filter(f => app.livingWikiIncludeDocuments || (!/^00-system\/|^07-genesis\/handoffs\//.test(f.path) &&
      (f.path.includes('/') || ['HOME.md','WALKTHROUGH.md'].includes(f.path))));
  for (const file of files) {
    const fm = meta(app, file);
    const n = {id:file.path, file, type:typeOf(app,file), label:fm.title || file.basename,
      recordType:fm.type || 'document', recordId:fm.id || '', frontmatter:fm,
      authority:fm.authority_tier || fm.certainty || fm.authority_scope || 'unspecified',
      status:fm.status || fm.relation_status || 'unspecified',
      permission:fm.current_claim_permission || 'unspecified',
      date:fm.updated || fm.created || '', candidate:fm.authority_tier==='candidate' ||
        fm.certainty==='candidate' || fm.relation_status==='candidate' || fm.status==='candidate'};
    nodes.push(n); byPath[n.id] = n;
    if (fm.id) {
      if (byRecord[fm.id]) { duplicates.add(fm.id); delete byRecord[fm.id]; }
      else if (!duplicates.has(fm.id)) byRecord[fm.id] = n;
    }
  }
  function resolve(raw, from) {
    const value = String(raw || '').trim();
    const m = value.match(/^\[\[([^\]|#]+)(?:[^\]]*)\]\]$/);
    const ref = m ? m[1] : value.replace(/#.*$/, '');
    if (duplicates.has(ref)) return null;
    if (byRecord[ref]) return byRecord[ref].id;
    if (byPath[ref]) return ref;
    const f = app.metadataCache.getFirstLinkpathDest(ref,from || '');
    return f && byPath[f.path] ? f.path : null;
  }
  const baseEdges = [], seen = new Set();
  function edge(source, target, kind, via) {
    if (!target || source === target) return;
    const key = JSON.stringify([source,target,kind]);
    if (seen.has(key)) return;
    seen.add(key); baseEdges.push({source,target,kind,via:via || source});
  }
  function refs(n,key,kind) {
    const resolved = [];
    for (const raw of list(n.frontmatter[key])) {
      const target = resolve(raw,n.id);
      if (target) { edge(n.id,target,kind); resolved.push(target); }
      else unresolved.push({source:n.id,field:key,reference:String(raw)});
    }
    return resolved;
  }
  for (const n of nodes) {
    if (n.type === 'RelO') {
      relations[n.id] = [...new Set([...(relations[n.id]||[]),...['participants','members','objects'].flatMap(k=>refs(n,k,'rel'))])];
    }
    for (const key of ['supporting_sources','sources','source_records','refs','counter_evidence','evidence_refs']) refs(n,key,'citation');
    for (const key of ['predecessor','successor','predecessors','successors','derived_from','supersedes']) refs(n,key,'lineage');
    for (const key of ['objects','relations','related_objects']) if (!(n.type === 'RelO' && key === 'objects')) refs(n,key,'appears');
    for (const raw of list(n.frontmatter.relations)) {
      const rid = resolve(raw,n.id);
      if (rid && byPath[rid].type === 'RelO') {
        relations[rid] = relations[rid] || [];
        if (!relations[rid].includes(n.id)) relations[rid].push(n.id);
      }
    }
    for (const target of Object.keys(app.metadataCache.resolvedLinks[n.id] || {})) {
      if (byPath[target]) edge(n.id,target,byPath[target].type === 'RefO' ? 'citation' : 'appears');
    }
  }
  // Original artifacts are separate, immutable witnesses, not canonical objects.
  for (const n of [...nodes]) {
    const path = n.frontmatter.original_path;
    if (typeof path !== 'string' || !path.startsWith('_originals/')) continue;
    const file = app.vault.getAbstractFileByPath(path);
    if (!file) { unresolved.push({source:n.id,field:'original_path',reference:path}); continue; }
    if (!byPath[path]) {
      const original = {id:path,file,type:'RefO',label:file.basename || file.name,
        recordType:'original-artifact',recordId:'',frontmatter:{},authority:'immutable original; checksum is integrity, not truth',
        status:'preserved',permission:'not a claim',date:'',candidate:false,original:true};
      nodes.push(original); byPath[path] = original;
    }
    edge(n.id,path,'citation');
  }
  const proposals = app.livingWikiProposals || [];
  for (const p of proposals) {
    if (['accepted','rejected','rejected-audit'].includes(p.reviewStatus)) continue;
    let body = p.body;
    if (typeof body === 'string') { try { body = JSON.parse(body); } catch { body = {}; } }
    const n = {id:p.path,file:null,type:p.kind === 'object-create' ? 'FO' : 'RNO',label:(body && body.title) || p.id,
      recordType:'proposal',recordId:p.id,frontmatter:{},authority:'candidate · level 7',status:p.reviewStatus || 'new',
      permission:'awaiting owner decision',date:p.received || '',candidate:true,proposal:p};
    nodes.push(n); byPath[n.id] = n;
    for (const raw of [...list(p.target_refs),...list(p.evidence_refs)]) edge(n.id,resolve(raw,n.id),'candidate');
    if (body && body.source_passage) edge(n.id,resolve(body.source_passage.path,n.id),'candidate');
  }
  const projected = [], adj = Object.create(null);
  for (const n of nodes) adj[n.id] = Object.create(null);
  // Bound expansion: a relation with many participants remains a star, not O(n²) links.
  for (const [rid,members] of Object.entries(relations)) {
    const unique = [...new Set(members)];
    if (unique.length <= 40) for (let i=0;i<unique.length;i++) for(let j=i+1;j<unique.length;j++) {
      projected.push({source:unique[i],target:unique[j],relos:[rid],kind:'projection',evidence:false});
    }
    for (const member of unique) edge(rid,member,'rel');
  }
  for (const e of baseEdges) {
    if (adj[e.source] && adj[e.target]) { adj[e.source][e.target]=e.kind; adj[e.target][e.source]=e.kind; }
  }
  return {nodes,byPath,byRecord,baseEdges,projected,relations,adj,unresolved,duplicateIds:[...duplicates]};
}
function buildFocusSet(app,model,id) {
  if (!model.byPath[id]) return null;
  const ids = [...new Set([id,...Object.keys(model.adj[id] || {}),...(model.relations[id] || [])])];
  return {coreId:id,ids,neighborIds:ids.filter(x=>x!==id)};
}
function matches(node, filters={}) {
  return (!filters.type || node.recordType===filters.type) &&
    (!filters.authority || String(node.authority).includes(filters.authority)) &&
    (!filters.permission || node.permission===filters.permission) &&
    (!filters.candidate || (filters.candidate==='candidate' ? node.candidate : !node.candidate)) &&
    (!filters.since || String(node.date).slice(0,10)>=filters.since);
}
module.exports={NOTE_TYPES,typeOf,buildModel,buildFocusSet,matches};
