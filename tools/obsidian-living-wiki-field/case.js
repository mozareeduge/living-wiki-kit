'use strict';
// A guided "case": one claim, the passage it cites, and a verdict the reader chooses.
// The case is data in the vault (WALKTHROUGH.md frontmatter `case:`). The verdict lives in plugin settings only;
// nothing here writes to the archive.
const {ItemView,TFile,parseYaml} = require('obsidian');

const STOP = new Set(['the','a','an','of','in','on','at','to','and','or','is','was','were','be','after','before','this','that','it','by','for','with','as']);
const words = text => String(text || '').toLowerCase().normalize('NFKC').match(/[\p{L}\p{N}']+/gu) || [];
const button = (el,text,fn,cls) => { const b=el.createEl('button',{text,cls}); b.addEventListener('click',fn); return b; };

async function caseOf(plugin) {
  const model=plugin.getModel();
  const home=model.byPath['WALKTHROUGH.md'];
  const file=home && plugin.app.vault.getAbstractFileByPath('WALKTHROUGH.md');
  if(!(file instanceof TFile)) return null;
  const m=/^---\r?\n([\s\S]*?)\r?\n---/.exec(await plugin.app.vault.cachedRead(file));
  let spec=null;
  try { spec=m && (parseYaml(m[1]) || {}).case; } catch(e) { return null; }
  if(!spec || !spec.claim_id) return null;
  const claim=model.nodes.find(n=>n.recordId===spec.claim_id);
  return claim ? {spec,claim,model} : null;
}

async function sourceText(plugin,claim,model) {
  const ref=[].concat(claim.frontmatter.supporting_sources || [])[0];
  const src=model.nodes.find(n=>n.recordId===ref);
  if(!src) return {text:'',src:null};
  const path=src.frontmatter.original_path;
  const file=path && plugin.app.vault.getAbstractFileByPath(path);
  const raw=file instanceof TFile ? await plugin.app.vault.cachedRead(file) : '';
  return {text:raw.split('\n').filter(l=>l.trim() && !/FICTIONAL WALKTHROUGH FIXTURE/.test(l)).join(' '),src};
}

function markGaps(el,statement,passage) {
  const known=new Set(words(passage));
  const gaps=[];
  for(const part of String(statement).split(/(\s+)/)) {
    const w=words(part)[0];
    if(w && !STOP.has(w) && !known.has(w)) { el.createEl('mark',{text:part,cls:'lwf-gap'}); gaps.push(w); }
    else el.appendText(part);
  }
  return gaps;
}

class CaseView extends ItemView {
  constructor(leaf,plugin){super(leaf);this.plugin=plugin;}
  getViewType(){return 'lwf-case-view';} getDisplayText(){return 'Case';} getIcon(){return 'search-check';}
  async onOpen(){this.contentEl.addClass('bbf-root','bbf-pane');await this.onOuterChange();}
  async onOuterChange(){
    const plugin=this.plugin,root=this.contentEl;
    root.empty();
    const wrap=root.createEl('div',{cls:'lwf-panel lwf-case'});
    const c=await caseOf(plugin);
    if(!c){
      wrap.createEl('h1',{text:'No case in this vault'});
      wrap.createEl('p',{text:'A case is a guided question about one claim. This vault does not define one.'});
      return;
    }
    const {spec,claim,model}=c, saved=(plugin.settings.caseVerdicts || {})[spec.claim_id];
    const {text:passage,src}=await sourceText(plugin,claim,model);

    wrap.createEl('div',{cls:'lwf-case-kicker',text:'Case file · '+(spec.minutes || 4)+' minutes'});
    wrap.createEl('h1',{text:spec.title || 'Is this claim supported?'});
    wrap.createEl('p',{cls:'lwf-case-lede',text:spec.brief || 'A colleague wants to cite the claim below. Check it against the passage it points to.'});

    const stage=wrap.createEl('div',{cls:'lwf-case-stage'});
    const claimBox=stage.createEl('section',{cls:'lwf-case-card'});
    claimBox.createEl('h3',{text:'The claim'});
    const q=claimBox.createEl('p',{cls:'lwf-case-quote',attr:{dir:'auto'}});
    const gaps=markGaps(q,claim.frontmatter.statement || claim.label,passage);
    claimBox.createEl('small',{text:'Candidate · '+claim.recordId+' · suggested, not accepted'});
    button(claimBox,'Show it on the map',()=>plugin.focusInField(claim.id));
    button(claimBox,'Open the claim record',()=>plugin.openReader(claim.id));

    const srcBox=stage.createEl('section',{cls:'lwf-case-card'});
    srcBox.createEl('h3',{text:'What the source actually says'});
    srcBox.createEl('p',{cls:'lwf-case-quote',text:passage || 'The cited source could not be read.',attr:{dir:'auto'}});
    srcBox.createEl('small',{text:src ? 'Source receipt · '+src.recordId+' · original is immutable' : 'No source cited'});
    if(src) button(srcBox,'Open the receipt',()=>plugin.openReader(src.id));

    const hint=wrap.createEl('p',{cls:'lwf-case-hint'});
    hint.setText(gaps.length
      ? 'Highlighted words appear in the claim but nowhere in the source.'
      : 'Every substantive word in the claim appears in the source. Wording still is not meaning, so judge it yourself.');

    const verdict=wrap.createEl('section',{cls:'lwf-case-verdict'});
    verdict.createEl('h3',{text:'Your verdict'});
    const options=spec.options || [{key:'supported',label:'Supported'},{key:'overstated',label:'Overstated'},{key:'unclear',label:'Needs more evidence'}];
    const row=verdict.createEl('div',{cls:'lwf-case-options'});
    const outcome=verdict.createEl('div',{cls:'lwf-case-outcome'});
    const show=key=>{
      outcome.empty();
      const right=key===spec.answer;
      outcome.createEl('p',{cls:right?'lwf-case-right':'lwf-case-close',text:right ? (spec.reveal_right || 'Right.') : (spec.reveal_other || 'Look again at the highlighted words.')});
      outcome.createEl('p',{text:'Your verdict is saved in this plugin only. The archive was not changed, and the claim stays a candidate until its owner decides.'});
      button(outcome,spec.next_label || 'Start with your own document',()=>plugin.app.workspace.openLinkText(spec.next_path || 'QUICKSTART.md','',true),'mod-cta');
    };
    for(const o of options) {
      const b=button(row,o.label,()=>{
        plugin.settings.caseVerdicts={...(plugin.settings.caseVerdicts || {}),[spec.claim_id]:o.key};
        plugin.persist();
        row.querySelectorAll('button').forEach(x=>x.classList.toggle('is-chosen',x===b));
        show(o.key);
      });
      if(saved===o.key) b.classList.add('is-chosen');
    }
    if(saved) show(saved);
  }
}

function install(PluginClass,FieldView) {
  const oldLoad=PluginClass.prototype.onload;
  PluginClass.prototype.onload=async function() {
    await oldLoad.call(this);
    this.registerView('lwf-case-view',leaf=>new CaseView(leaf,this));
    this.addCommand({id:'open-Case',name:'Open the case',callback:()=>this.activate('lwf-case-view')});
    this.app.workspace.onLayoutReady(async()=>{
      if(await caseOf(this) && !(this.settings.caseVerdicts && Object.keys(this.settings.caseVerdicts).length) && !this.settings.caseSeen) {
        this.settings.caseSeen=true; this.persist();
        this.activate('lwf-case-view');
      }
    });
  };
  const oldBuild=FieldView.prototype.buildGraph;
  FieldView.prototype.buildGraph=function() {
    oldBuild.call(this);
    if(!this.nodeSel) return;
    caseOf(this.plugin).then(c=>{ if(c && this.nodeSel) this.nodeSel.attr('data-case',d=>d.recordId===c.spec.claim_id?'true':null); });
  };
  const oldUnload=PluginClass.prototype.onunload;
  PluginClass.prototype.onunload=function() { oldUnload.call(this); this.app.workspace.detachLeavesOfType('lwf-case-view'); };
}
module.exports={install,caseOf,markGaps};
