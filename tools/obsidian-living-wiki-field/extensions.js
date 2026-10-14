'use strict';
const {ItemView,MarkdownRenderer,TFile,Notice,PluginSettingTab,Setting,Component} = require('obsidian');
const {spawn} = require('child_process');
const {matches,buildFocusSet} = require('./model');
const button = (el,text,fn) => { const b=el.createEl('button',{text}); b.addEventListener('click',fn); return b; };
const readJson = async (app,path) => {
  if (!await app.vault.adapter.exists(path)) return null;
  return JSON.parse(await app.vault.adapter.read(path));
};
function textBlock(el,tag,text,cls) { return el.createEl(tag,{text:String(text == null ? '' : text),cls}); }
function install(PluginClass,FieldView,ReaderView,IndexView) {
  const oldLoad=PluginClass.prototype.onload;
  PluginClass.prototype.onload=async function() {
    this.settings={python:process.platform==='win32'?'python':'python3',...await this.loadData()};
    this.routeEvents=this.settings.routeEvents || [];
    this.filters={}; this.app.livingWikiProposals=[]; this.health=null; this.recordsError=null;
    oldLoad.call(this);
    this.routeEvents=(this.settings.routeEvents || []).slice(-11);
    this.registerView('lwf-review-view',leaf=>new ReviewView(leaf,this));
    this.registerView('lwf-health-view',leaf=>new HealthView(leaf,this));
    this.addCommand({id:'open-Review',name:'Open Review queue',callback:()=>this.activate('lwf-review-view')});
    this.addCommand({id:'open-Health',name:'Open archive health',callback:()=>this.activate('lwf-health-view')});
    this.addSettingTab(new FieldSettings(this.app,this));
    this.registerEvent(this.app.vault.on('modify',f=>{if(f.path.startsWith('_proposals/'))this.loadProposals();}));
    this.registerEvent(this.app.vault.on('create',f=>{if(f.path.startsWith('_proposals/'))this.loadProposals();}));
    this.registerEvent(this.app.vault.on('delete',f=>{if(f.path.startsWith('_proposals/'))this.loadProposals();}));
    const invalidate=()=>{if(this.health && !this.health.running){this.health.stale=true;this.refreshAll();}};
    for(const event of ['modify','create','delete','rename'])this.registerEvent(this.app.vault.on(event,invalidate));
    await this.loadProposals();
  };
  PluginClass.prototype.persist=function() {
    clearTimeout(this.persistTimer);
    this.persistTimer=setTimeout(()=>this.saveData({...this.settings,routeEvents:this.routeEvents}),250);
  };
  PluginClass.prototype.loadProposals=async function() {
    const proposals=[],terminal=new Map(); this.recordsError=null;
    try {
      const files=this.app.vault.getFiles().filter(f=>/^_proposals\/(records|adjudications)\/.+\.json$/.test(f.path));
      const records=await Promise.all(files.map(async f=>({...JSON.parse(await this.app.vault.read(f)),path:f.path})));
      for(const d of records) if(d.type==='adjudication' && ['accepted','rejected'].includes(d.decision)) terminal.set(d.proposal_id,d.decision);
      for(const d of records) if(d.type==='proposal') proposals.push({...d,reviewStatus:terminal.get(d.id)||'new'});
      // Reuse the audited candidate projection's verdicts when it exists.
      const projections=await readJson(this.app,'_search/candidate_projections.json');
      if(projections) for(const p of proposals) {
        const projected=(projections.projections || []).find(d=>d.proposal_id===p.id);
        if(projected && !terminal.has(p.id)) p.reviewStatus=projected.proposal_status;
      }
      this.app.livingWikiProposals=proposals;
    } catch(e) {
      this.app.livingWikiProposals=[]; this.recordsError='Proposal data unreadable: '+e.message;
    }
    this.model=null; this.refreshAll();
  };
  const oldRefresh=PluginClass.prototype.refreshAll;
  PluginClass.prototype.refreshAll=function() { oldRefresh.call(this); this.persist(); };
  const oldClose=PluginClass.prototype.onunload;
  PluginClass.prototype.onunload=function() {
    oldClose.call(this); delete this.app.livingWikiProposals;
    for(const type of ['lwf-review-view','lwf-health-view']) this.app.workspace.detachLeavesOfType(type);
    if(this.validationProcess) this.validationProcess.kill();
  };
  PluginClass.prototype.visit=function(id) {
    if(!this.getModel().byPath[id]) return;
    this.activeId=id;
    if(!this.routeEvents.length || this.routeEvents[this.routeEvents.length-1].id!==id) {
      this.routeEvents.push({id,label:this.model.byPath[id].label,source:'reader',index:this.routeEvents.length+1});
      this.routeEvents=this.routeEvents.slice(-11);
    }
    this.refreshAll();
  };
  const oldOpen=PluginClass.prototype.openReader;
  PluginClass.prototype.openReader=function(id) { this.visit(id); oldOpen.call(this,id); };
  PluginClass.prototype.setReaderOpen=function(open) {
    this.readerOpen=open;
    for(const leaf of this.app.workspace.getLeavesOfType('lwf-field-view')) {
      const main=leaf.view.contentEl.querySelector('.bbf-main');
      if(main)main.classList.toggle('reader-open',open);
    }
  };
  const oldFocus=FieldView.prototype.focusObject;
  FieldView.prototype.focusObject=function(id,opts) { this.plugin.visit(id); oldFocus.call(this,id,opts); };
  const oldFieldOpen=FieldView.prototype.onOpen;
  FieldView.prototype.onOpen=async function() {
    oldFieldOpen.call(this);
    if(!this.svg) this.initGraph();
    // Enter directly; the inherited poetic threshold remains available in About.
    const threshold=this.contentEl.querySelector('#bbfThreshold'); if(threshold)threshold.remove();
    const rail=this.contentEl.querySelector('.bbf-rail') || this.contentEl;
    button(rail,'REVIEW',()=>this.plugin.activate('lwf-review-view'));
    button(rail,'HEALTH',()=>this.plugin.activate('lwf-health-view'));
    const note=this.contentEl.createEl('div',{cls:'lwf-contract',text:'Archive view · projected edges are navigation, never evidence · candidates remain marked'});
    note.setAttribute('role','note');
  };
  const oldVisible=FieldView.prototype.nodeVisible;
  FieldView.prototype.nodeVisible=function(id) {
    const n=this.plugin.getModel().byPath[id];
    return !!n && matches(n,this.plugin.filters) && oldVisible.call(this,id);
  };
  const oldBuild=FieldView.prototype.buildGraph;
  FieldView.prototype.buildGraph=function() {
    oldBuild.call(this);
    if(this.nodeSel) this.nodeSel.attr('data-candidate',d=>d.candidate?'true':'false')
      .attr('aria-label',d=>d.label+' · '+d.recordType+' · '+d.authority)
      .selectAll('title').data(d=>[d]).join('title').text(d=>d.label+' · '+d.recordType+' · '+d.authority);
    if(this.nodeSel)this.nodeSel.select('text').text(d=>(d.candidate?'[C] ':'')+d.label);
    if(this.projSel)this.projSel.attr('stroke-dasharray','3 6');
  };
  FieldView.prototype.refresh=function(force) {
    if(!this.svg)return;
    const model=this.plugin.getModel();
    if(force || this.renderedModel!==model){this.buildGraph();this.renderedModel=model;}
    else {this.updateVisibility();this.renderRoute();this.renderFieldViewControls();}
  };
  FieldView.prototype.onOuterChange=function(){this.refresh(false);};
  for(const View of [FieldView,ReaderView]) {
    const oldClose=View.prototype.onClose;
    View.prototype.onClose=function(){
      this.readToken=(this.readToken||0)+1;
      if(this.renderComponent)this.renderComponent.unload();
      if(oldClose)oldClose.call(this);
      if(this.svg){this.svg=null;this.root=null;}
    };
  }
  const originalActivate=PluginClass.prototype.activate;
  PluginClass.prototype.activate=function(type) {
    const existing=this.app.workspace.getLeavesOfType(type)[0];
    if(existing){this.app.workspace.revealLeaf(existing);if(existing.view.onOuterChange)existing.view.onOuterChange();}
    else originalActivate.call(this,type);
  };
  const oldView=FieldView.prototype.renderViewDrawer;
  // The inherited drawer is named renderTypeToggles in some plugin builds.
  const filterDrawer=Object.keys(FieldView.prototype).find(k=>k==='renderFieldViewControls'||k==='renderTypeToggles'||k==='renderViewDrawer');
  if(filterDrawer) {
    const original=FieldView.prototype[filterDrawer];
    FieldView.prototype[filterDrawer]=function() {
      original.call(this);
      const root=this.contentEl.querySelector('#bbfTypeToggles');
      if(root) makeFilters(root,this.plugin);
    };
  }
  FieldView.prototype.renderReader=function(id) {
    const root=this.contentEl.querySelector('#bbfReader');
    if(root) renderReader(this,root,id);
  };
  ReaderView.prototype.refresh=function() { renderReader(this,this.body,this.plugin.activeId); };
  const oldIndex=IndexView.prototype.refresh;
  IndexView.prototype.refresh=function() {
    oldIndex.call(this);
    if(this.body) {
      const filters=this.body.createEl('div',{cls:'lwf-filter-panel'});
      makeFilters(filters,this.plugin);
      // Replace inherited inventory with an exact, filterable native list.
      const input=this.body.querySelector('.bbf-search'),list=this.body.querySelector('.bbf-index-list');
      const redraw=()=>{
        list.empty(); const q=(input.value||'').toLowerCase();
        const nodes=this.plugin.getModel().nodes.filter(n=>matches(n,this.plugin.filters) &&
          (!q || [n.label,n.recordType,n.recordId,n.authority].join(' ').toLowerCase().includes(q)));
        textBlock(list,'p',nodes.length+' matching records. Showing up to 300; narrow the search for more.');
        for(const n of nodes.slice(0,300)) {
          const row=list.createEl('div',{cls:'lwf-record-row'});
          button(row,n.label,()=>this.plugin.openReader(n.id));
          textBlock(row,'small',(n.candidate?'CANDIDATE · ':'')+n.recordType+' · '+n.authority);
          button(row,'Field',()=>this.plugin.focusInField(n.id));
        }
      };
      input.addEventListener('input',redraw); redraw();
    }
  };
}
function makeFilters(el,plugin) {
  const model=plugin.getModel();
  textBlock(el,'h3','View filters');
  for(const [key,label,values] of [
    ['type','Record type',[...new Set(model.nodes.map(n=>n.recordType))]],
    ['authority','Authority as recorded',[...new Set(model.nodes.map(n=>n.authority))]],
    ['permission','Claim permission',[...new Set(model.nodes.map(n=>n.permission))]],
    ['candidate','Candidate state',['candidate','recorded']]]) {
    const lab=el.createEl('label',{text:label}),select=lab.createEl('select');
    select.createEl('option',{value:'',text:'All'});
    for(const v of values)select.createEl('option',{value:String(v),text:String(v)});
    select.value=plugin.filters[key]||'';
    select.addEventListener('change',()=>{plugin.filters[key]=select.value;plugin.refreshAll();});
  }
  const date=el.createEl('label',{text:'Updated since'}).createEl('input',{type:'date'});
  date.value=plugin.filters.since||'';
  date.addEventListener('change',()=>{plugin.filters.since=date.value;plugin.refreshAll();});
  button(el,'Reset filters',()=>{plugin.filters={};plugin.refreshAll();});
}
async function renderReader(view,root,id) {
  if(!root)return;
  const token=(view.readToken||0)+1;view.readToken=token;root.empty();
  if(view.renderComponent)view.renderComponent.unload();
  view.renderComponent=new Component();view.renderComponent.load();
  const plugin=view.plugin,model=plugin.getModel(),node=model.byPath[id];
  if(!node) {textBlock(root,'p','Select a record in Field or Index.');return;}
  textBlock(root,'div',(node.candidate?'CANDIDATE · ':'')+node.recordType+' · '+node.authority,'lwf-evidence-badge');
  textBlock(root,'h2',node.label);
  textBlock(root,'p','Status: '+node.status+' · Permission: '+node.permission);
  const nav=root.createEl('div',{cls:'lwf-evidence-links'});
  textBlock(nav,'h3','Trace and related records');
  const focus=buildFocusSet(plugin.app,model,id);
  for(const target of (focus ? focus.neighborIds : [])) {
    const n=model.byPath[target];button(nav,n.label+' · '+n.recordType,()=>plugin.openReader(target));
  }
  if(!(focus && focus.neighborIds.length))textBlock(nav,'p','No recorded neighbors. Search similarity does not establish a relation.');
  if(node.proposal) {
    textBlock(root,'pre',JSON.stringify(node.proposal,null,2),'lwf-json');
    textBlock(root,'p','Owner adjudication is required. This view cannot accept, reject or apply a proposal.');
    return;
  }
  if(node.original) {
    textBlock(root,'p','Immutable original. The checksum detects altered bytes; it does not prove a statement.');
    button(root,'Inspect original',()=>plugin.app.workspace.openLinkText(node.id,'',true));
  }
  const file=plugin.app.vault.getAbstractFileByPath(node.id);
  if(!(file instanceof TFile))return;
  if(node.original && !['md','txt','csv','html'].includes(file.extension))return;
  const text=await plugin.app.vault.cachedRead(file);
  if(view.readToken!==token)return;
  const prose=root.createEl('div',{cls:'bbf-prose',attr:{dir:'auto'}});
  if(node.original)textBlock(prose,'pre',text);
  else {
    await MarkdownRenderer.render(plugin.app,text,prose,file.path,view.renderComponent);
    if(view.readToken!==token)return;
    prose.querySelectorAll('input[type="checkbox"]').forEach(el=>el.disabled=true);
    prose.addEventListener('click',e=>{
      const link=e.target.closest('a.internal-link');
      if(!link)return;e.preventDefault();e.stopPropagation();
      const dest=plugin.app.metadataCache.getFirstLinkpathDest(link.getAttribute('data-href')||link.getAttribute('href'),file.path);
      if(dest && model.byPath[dest.path])plugin.openReader(dest.path);
      else if(dest)plugin.app.workspace.openLinkText(dest.path,file.path,true);
    });
  }
  const related=root.createEl('div',{cls:'lwf-related'});
  textBlock(related,'h3','Context hints · not evidence');
  try {
    const packs=plugin.app.vault.getFiles().filter(f=>f.path.startsWith('_search/packs/')&&f.extension==='json');
    for(const f of packs.slice(-30)) {
      const pack=JSON.parse(await plugin.app.vault.read(f));
      if(view.readToken!==token)return;
      if(![node.recordId,node.id].includes(pack.seed_id||pack.seed||(pack.meta||{}).seed))continue;
      for(const rec of (pack.records||[]).slice(0,30)) {
        const target=model.byRecord[rec.id]||model.byPath[rec.path];
        if(target && target.id!==node.id) button(related,target.label+' · '+(rec.reason||'context hint'),()=>plugin.openReader(target.id));
      }
      break;
    }
    if(related.children.length===1)textBlock(related,'p','No saved context pack for this record. Recorded neighbors remain available above.');
  } catch(e) {textBlock(related,'p','Context hints unavailable: '+e.message);}
}
class ReviewView extends ItemView {
  constructor(leaf,plugin){super(leaf);this.plugin=plugin;}
  getViewType(){return 'lwf-review-view';} getDisplayText(){return 'Review';} getIcon(){return 'clipboard-list';}
  async onOpen(){this.onOuterChange();}
  onOuterChange(){
    const root=this.contentEl;root.empty();root.addClass('lwf-panel');
    textBlock(root,'h1','Review queue');
    textBlock(root,'p','Candidate proposals are visible here. Only the owner decides authority.');
    button(root,'Refresh queue',()=>this.plugin.loadProposals());
    if(this.plugin.recordsError){textBlock(root,'p',this.plugin.recordsError,'lwf-error');return;}
    const proposals=this.plugin.app.livingWikiProposals||[];
    textBlock(root,'p',proposals.length+' durable proposals · '+proposals.filter(p=>!['accepted','rejected'].includes(p.reviewStatus)).length+' awaiting a decision');
    if(!proposals.length)textBlock(root,'p','No proposals yet. An empty queue is expected in a new kit.');
    for(const p of proposals){
      const row=root.createEl('details',{cls:'lwf-proposal'});
      textBlock(row,'summary',p.id+' · '+p.kind+' · '+p.reviewStatus+' · CANDIDATE');
      textBlock(row,'pre',JSON.stringify(p,null,2),'lwf-json');
      if(this.plugin.getModel().byPath[p.path])button(row,'Read candidate and trace',()=>this.plugin.openReader(p.path));
    }
  }
}
class HealthView extends ItemView {
  constructor(leaf,plugin){super(leaf);this.plugin=plugin;}
  getViewType(){return 'lwf-health-view';} getDisplayText(){return 'Archive health';} getIcon(){return 'shield-check';}
  async onOpen(){await this.onOuterChange();}
  async onOuterChange(){
    const root=this.contentEl;root.empty();root.addClass('lwf-panel');textBlock(root,'h1','Archive health');
    try {
      const state=await readJson(this.plugin.app,'00-system/registers/CORPUS_STATE.json');
      if(state)textBlock(root,'p','Registered: '+state.source_material_count+' · Held: '+state.held_artifact_count+' · Snapshot: '+state.id);
      else textBlock(root,'p','No corpus register. This vault has not been initialized from the kit.');
      const model=this.plugin.getModel();
      textBlock(root,'p',model.nodes.length+' visible records · '+model.unresolved.length+' unresolved references · '+model.duplicateIds.length+' duplicate IDs');
      textBlock(root,'p','These are register and view counts. They are not a passing validation result.');
      button(root,this.plugin.validationProcess?'Checking…':'Run governance checks',()=>this.plugin.validateNow());
      if(this.plugin.health){
        textBlock(root,'h2',this.plugin.health.running?'Checks running':this.plugin.health.stale?'Changed since check · recheck required':this.plugin.health.passed?'Checks passed':'Check failed');
        textBlock(root,'p','Observed '+this.plugin.health.time+'; later edits require another check.');
        textBlock(root,'pre',this.plugin.health.output,'lwf-json');
      }else textBlock(root,'p','Unverified in this view. Run the checks to see current evidence.');
    }catch(e){textBlock(root,'p','Register unreadable: '+e.message,'lwf-error');}
  }
}
// Python commands are launched with argv and shell disabled, one at a time; all are checks.
function runCheck(plugin,args) {
  return new Promise(resolve=>{
    const base=plugin.app.vault.adapter.getBasePath && plugin.app.vault.adapter.getBasePath();
    if(!base){resolve({code:1,text:'Local filesystem vault required.'});return;}
    const child=spawn(plugin.settings.python,args,{cwd:base,shell:false,windowsHide:true});plugin.validationProcess=child;
    let output='';const append=d=>{output=(output+d.toString()).slice(-20000);};
    child.stdout.on('data',append);child.stderr.on('data',append);
    const timer=setTimeout(()=>{append('\nCheck timed out after 120 seconds.');child.kill();},120000);
    child.on('error',e=>{clearTimeout(timer);resolve({code:1,text:e.message});});
    child.on('close',code=>{clearTimeout(timer);resolve({code:code===0?0:1,text:output});});
  });
}
class FieldSettings extends PluginSettingTab {
  constructor(app,plugin){super(app,plugin);this.plugin=plugin;}
  display(){this.containerEl.empty();new Setting(this.containerEl).setName('Python interpreter').setDesc('Local Python used only for the four governance checks.').addText(t=>t.setValue(this.plugin.settings.python).onChange(v=>{this.plugin.settings.python=v.trim();this.plugin.persist();}));}
}
const originalInstall=install;
module.exports.install=function(PluginClass,...views){
  originalInstall(PluginClass,...views);
  PluginClass.prototype.validateNow=async function(){
    if(this.validationProcess)return;
    this.health={running:true,passed:false,time:new Date().toISOString(),output:''};this.refreshAll();
    for(const args of [['scripts/wiki_validate.py','--repo','.','--format','json'],['scripts/wiki_state.py','--repo','.','check'],['scripts/wiki_evidence.py','--repo','.','check'],['scripts/wiki_profiles.py','check']]){
      const result=await runCheck(this,args);this.validationProcess=null;
      this.health.output+=args.join(' ')+'\n'+result.text+'\n';
      if(result.code){this.health.running=false;this.refreshAll();return;}
    }
    this.health.running=false;this.health.passed=true;this.refreshAll();new Notice('Living Wiki: governance checks passed.');
  };
};
