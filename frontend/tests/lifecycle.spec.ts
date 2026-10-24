import { expect, test } from '@playwright/test';

test('create a business and complete an authorized recovery with reconciled books', async ({ page, request }, testInfo) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  const root='/api/simulations/demo_001';
  expect((await request.post(root+'/reset')).ok()).toBeTruthy();
  const errors: string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/economy/businesses');
  await page.getByRole('button',{name:'Create business',exact:true}).click();
  await page.getByLabel('Business name',{exact:true}).fill('Browser QA '+testInfo.project.name);
  await page.getByRole('button',{name:'Deploy business',exact:true}).click();
  await expect(page.getByText('Business created. Its team is ready for the next economy tick.')).toBeVisible();
  await page.goto('/economy/world');
  await expect(page.getByRole('main')).toBeVisible();
  const width=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
  expect(width.scroll).toBeLessThanOrEqual(width.w+1);
  await page.screenshot({path:`../docs/evidence/world-${testInfo.project.name}.png`,fullPage:true});
  expect((await request.post(root+'/shock',{data:{type:'supplier_bankruptcy',supplier_id:'northstar_roasters'}})).ok()).toBeTruthy();
  for(let i=0;i<4;i++) expect((await request.post(root+'/tick')).ok()).toBeTruthy();
  const state=await (await request.get(root)).json();
  expect(state.contracts.some((c:{recovery:boolean;payment_state:string})=>c.recovery&&c.payment_state==='RECONCILED')).toBeTruthy();
  expect(state.reconciliation.every((r:{ok:boolean})=>r.ok)).toBeTruthy();
  expect(state.audit.valid).toBeTruthy();
  await page.goto('/economy/control-tower');
  // Preserve actual route contract and use the navigation if a future route changes.
  if(!await page.getByRole('heading',{name:'Money moves. The books remember.'}).count()) await page.getByRole('link',{name:'Control tower',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Money moves. The books remember.'})).toBeVisible();
  await page.screenshot({path:`../docs/evidence/finance-${testInfo.project.name}.png`,fullPage:true});
  await page.goto('/economy/negotiations');
  await expect(page.getByRole('heading',{name:'Offers, counteroffers, consequences.'})).toBeVisible();
  await page.screenshot({path:`../docs/evidence/negotiations-${testInfo.project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});
