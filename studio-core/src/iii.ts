// Minimal structural view of the iii SDK that the iii-backed stores need, so
// studio-core doesn't take a hard dependency on iii-sdk's exported types.
export interface TriggerFn {
  trigger<TInput, TOutput>(request: { function_id: string; payload: TInput }): Promise<TOutput>
}
