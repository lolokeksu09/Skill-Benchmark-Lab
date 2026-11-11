const queue=document.querySelector('#queue');
const feedback=document.querySelector('#feedback');
window.queueApi.list({query:'',status:'all'}).then(({items})=>{
  queue.innerHTML=items.map(item=>`<article class="card" data-id="${item.id}"><h2>${item.title}</h2><p>${item.note}</p><button class="bookmark" aria-pressed="${item.saved}">★</button></article>`).join('');
  feedback.textContent=`${items.length} requests`;
});