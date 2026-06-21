// WikiStore backed by iii state (scope "studio-wiki"), keyed by slug.
import type { TriggerFn } from '../runtime/iii-store.js'
import type { WikiPage, WikiStore } from './wiki-store.js'

const SCOPE = 'studio-wiki'

export class IiiWikiStore implements WikiStore {
  constructor(private iii: TriggerFn) {}

  async get(slug: string): Promise<WikiPage | null> {
    const v = await this.iii.trigger<{ scope: string; key: string }, WikiPage | null>({
      function_id: 'state::get',
      payload: { scope: SCOPE, key: slug },
    })
    return v ?? null
  }

  async put(page: WikiPage): Promise<WikiPage> {
    await this.iii.trigger<{ scope: string; key: string; value: WikiPage }, unknown>({
      function_id: 'state::set',
      payload: { scope: SCOPE, key: page.slug, value: page },
    })
    return page
  }

  async list(): Promise<WikiPage[]> {
    const v = await this.iii.trigger<{ scope: string }, WikiPage[]>({
      function_id: 'state::list',
      payload: { scope: SCOPE },
    })
    return v ?? []
  }
}
