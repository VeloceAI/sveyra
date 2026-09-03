import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  DEFAULT_LOGIN_REDIRECT,
  sanitizeLoginRedirect,
} from "./sanitize-login-redirect.ts";

describe("sanitizeLoginRedirect", () => {
  it("returns the default for null, empty, and whitespace", () => {
    assert.equal(sanitizeLoginRedirect(null), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect(""), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("   "), DEFAULT_LOGIN_REDIRECT);
  });

  it("accepts safe relative paths", () => {
    assert.equal(sanitizeLoginRedirect("/wardrobe"), "/wardrobe");
    assert.equal(sanitizeLoginRedirect("/profile?tab=style"), "/profile?tab=style");
    assert.equal(sanitizeLoginRedirect(" /recommend "), "/recommend");
  });

  it("rejects absolute URLs with a scheme", () => {
    assert.equal(sanitizeLoginRedirect("http://evil.com"), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("https://evil.com/path"), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("javascript:alert(1)"), DEFAULT_LOGIN_REDIRECT);
  });

  it("rejects protocol-relative URLs", () => {
    assert.equal(sanitizeLoginRedirect("//evil.com"), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("///evil.com"), DEFAULT_LOGIN_REDIRECT);
  });

  it("rejects backslash variants", () => {
    assert.equal(sanitizeLoginRedirect("\\evil.com"), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("/\\evil.com"), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("\\/evil.com"), DEFAULT_LOGIN_REDIRECT);
  });

  it("rejects paths without a leading slash", () => {
    assert.equal(sanitizeLoginRedirect("wardrobe"), DEFAULT_LOGIN_REDIRECT);
    assert.equal(sanitizeLoginRedirect("evil.com"), DEFAULT_LOGIN_REDIRECT);
  });
});
