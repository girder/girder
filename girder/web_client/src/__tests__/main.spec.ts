import { describe, it, expect } from 'vitest';
import '@girder/core/utilities/jquery/jquery';
import '@girder/core/main';

describe('main', () => {
  it('sets girder on window', () => {
    // @ts-ignore
    expect(window.girder).not.toBeNull();
  });
});
