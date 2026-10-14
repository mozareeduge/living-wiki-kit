'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const {buildModel,buildFocusSet,matches}=require('./model');
function appFor(records,proposals=[]) {
  const files=Object.entries(records).map(([path,fm])=>({path,basename:path.split('/').pop().replace(/\.md$/,''),fm}));
  return {livingWikiProposals:proposals,vault:{getMarkdownFiles:()=>files,getAbstractFileByPath:p=>files.find(f=>f.path===p),modify:()=>{throw Error('write forbidden');}},
    metadataCache:{getFileCache:f=>({frontmatter:f.fm}),getFirstLinkpathDest:p=>files.find(f=>f.path===p||f.path===p+'.md'||f.basename===p),resolvedLinks:{}}};
}
test('kit participants resolve by ID and projections retain generating relation',()=>{
  const app=appFor({'03-objects/a.md':{id:'ab-obj-a',type:'object'},'03-objects/b.md':{id:'ab-obj-b',type:'object'},'06-relations/r.md':{id:'ab-rel-r',type:'relation-object',participants:['ab-obj-a','[[03-objects/b]]']}});
  const m=buildModel(app);assert.equal(m.byPath['06-relations/r.md'].type,'RelO');assert.equal(m.projected.length,1);
  assert.deepEqual(m.projected[0].relos,['06-relations/r.md']);assert.equal(m.projected[0].evidence,false);
  assert.equal(buildFocusSet(app,m,'06-relations/r.md').neighborIds.length,2);
});
test('claim source trace and immutable original remain distinct nodes',()=>{
  const app=appFor({'05-claims/c.md':{type:'claim-object',supporting_sources:['ab-src-0123456789ab']},'02-sources/records/s.md':{id:'ab-src-0123456789ab',type:'source-record',original_path:'_originals/a.md'},'_originals/a.md':{type:'document'}});
  const m=buildModel(app);assert.equal(m.byPath['02-sources/records/s.md'].type,'RefO');assert.equal(m.byPath['_originals/a.md'].original,true);
  assert.equal(m.baseEdges.filter(e=>e.kind==='citation').length,2);assert.equal(m.byPath['05-claims/c.md'].authority,'unspecified');
});
test('candidate proposal is explicit and terminal proposals do not appear as canonical objects',()=>{
  const app=appFor({'03-objects/a.md':{id:'ab-obj-a',type:'object'}},[
    {id:'p1',path:'_proposals/records/2026/p1.json',kind:'object-create',body:'{"title":"Candidate"}',target_refs:['ab-obj-a'],reviewStatus:'new'},
    {id:'p2',path:'_proposals/records/2026/p2.json',kind:'object-create',reviewStatus:'accepted'}]);
  const m=buildModel(app);assert.equal(m.byPath['_proposals/records/2026/p1.json'].authority,'candidate · level 7');assert.equal(m.byPath['_proposals/records/2026/p1.json'].candidate,true);
  assert.equal(m.byPath['_proposals/records/2026/p2.json'],undefined);assert.equal(m.baseEdges[0].kind,'candidate');
});
test('duplicate IDs and unresolved references are reported instead of choosing a witness',()=>{
  const m=buildModel(appFor({'03-objects/a.md':{id:'dup',type:'object'},'03-objects/b.md':{id:'dup',type:'object'},'06-relations/r.md':{type:'relation-object',participants:['dup','missing']}}));
  assert.deepEqual(m.duplicateIds,['dup']);assert.equal(m.baseEdges.length,0);assert.equal(m.unresolved.length,2);
});
test('large hyperedges stay linear and build is pure across repeated reads',()=>{
  const records={'06-relations/r.md':{type:'relation-object',participants:[]}};
  for(let i=0;i<100;i++){records['03-objects/'+i+'.md']={id:'ab-obj-'+i,type:'object'};records['06-relations/r.md'].participants.push('ab-obj-'+i);}
  const app=appFor(records),before=JSON.stringify(records),m=buildModel(app);
  assert.equal(m.projected.length,0);assert.equal(m.baseEdges.length,100);assert.equal(JSON.stringify(records),before);assert.deepEqual(buildModel(app).baseEdges,m.baseEdges);
});
test('view filters do not change record identity or authority',()=>{
  const n={recordType:'claim-object',authority:'candidate',permission:'may-note',date:'2026-10-14',candidate:true};
  assert.equal(matches(n,{type:'claim-object',candidate:'candidate',since:'2026-10-01'}),true);
  assert.equal(matches(n,{candidate:'recorded'}),false);assert.equal(n.authority,'candidate');
});
test('candidate authority on recorded notes is visible and filterable',()=>{
  const m=buildModel(appFor({'03-objects/a.md':{type:'object',authority_tier:'candidate'},'05-claims/c.md':{type:'claim-object',certainty:'candidate'},'06-relations/r.md':{type:'relation-object',relation_status:'candidate'}}));
  for(const n of m.nodes){assert.equal(n.candidate,true);assert.equal(matches(n,{candidate:'candidate'}),true);assert.equal(matches(n,{candidate:'recorded'}),false);}
});
test('archive focus defaults to knowledge records; system documents remain an explicit option',()=>{
  const app=appFor({'README.md':{},'HOME.md':{},'00-system/manual.md':{},'07-genesis/handoffs/h.md':{},'03-objects/a.md':{type:'object'}});
  assert.deepEqual(buildModel(app).nodes.map(n=>n.id),['HOME.md','03-objects/a.md']);
  app.livingWikiIncludeDocuments=true;assert.equal(buildModel(app).nodes.length,5);
});
