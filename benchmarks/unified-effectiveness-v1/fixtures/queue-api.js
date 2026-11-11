/* Fixed test-only, fictional API. Caller may not modify. */
(() => {
  const records = [
    {id:'r1',title:'Replace scanner battery',note:'Unit 14, loading dock',status:'open',saved:false,version:1},
    {id:'r2',title:'Inspect backup generator',note:'Scheduled service checklist',status:'open',saved:true,version:3},
    {id:'r3',title:'Close pump ticket',note:'Final inspection is complete',status:'done',saved:false,version:4},
    {id:'r4',title:'Calibrate access panel',note:'South entrance, panel C',status:'open',saved:false,version:2},
    {id:'r5',title:'<img src=x onerror="window.__injected=true">',note:'Untrusted markup must stay plain text',status:'done',saved:false,version:1},
    {id:'r6',title:'Fast router inspection',note:'Priority service check',status:'open',saved:false,version:1},
  ];
  const clone=x=>JSON.parse(JSON.stringify(x));
  let rejectToggle=false;
  const delay=(ms,signal)=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},ms);
    function abort(){clearTimeout(timer);reject(Object.assign(new Error('aborted'),{name:'AbortError'}));}
    if(signal){if(signal.aborted){abort();return;}signal.addEventListener('abort',abort,{once:true});}
  });
  window.queueApi = {
    async list({query='',status='all',signal}={}) {
      const normalized=String(query).trim().toLowerCase();
      const sleep=normalized==='slow'?160:normalized==='fast'?8:15;
      await delay(sleep,signal);
      if(normalized==='error')throw new Error('Service temporarily unavailable');
      if(!['all','open','done'].includes(status))throw new Error('invalid status');
      let filtered=records.filter(r => (status==='all'||r.status===status) && (!normalized||r.title.toLowerCase().includes(normalized)||r.note.toLowerCase().includes(normalized)));
      if(normalized==='slow')filtered=[records[0]];
      if(normalized==='fast')filtered=[records[5]];
      return {items:clone(filtered),nextCursor:null};
    },
    async toggle(id, saved) {
      await delay(5);
      if(rejectToggle){rejectToggle=false;throw Object.assign(new Error('conflict'),{status:409});}
      const r=records.find(x=>x.id===id);if(!r)throw new Error('not found');
      if(Boolean(saved)!==r.saved){r.saved=Boolean(saved);r.version++;}
      return clone({saved:r.saved,version:r.version});
    },
    rejectNextToggle() {rejectToggle=true;},
  };
})();
