import test from "node:test";
import assert from "node:assert/strict";
import { executeShare } from "../handleShareReport.js";

test("executeShare - vazio retorna empty", async () => {
  const result = await executeShare("", {
    navigatorShare: async () => {},
    locationAssign: () => {},
  });
  assert.equal(result.status, "empty");
});

test("executeShare - sucesso retorna shared", async () => {
  let shareCalled = false;
  let shareArgs = null;
  const result = await executeShare("Meu texto", {
    navigatorShare: async (args) => {
      shareCalled = true;
      shareArgs = args;
    },
    locationAssign: () => {
      throw new Error("Não deve chamar locationAssign");
    },
  });

  assert.equal(result.status, "shared");
  assert.equal(shareCalled, true);
  assert.equal(shareArgs.title, "Relatório Técnico - Operação Lei Seca");
  assert.equal(shareArgs.text, "Meu texto");
  assert.equal(shareArgs.url, undefined, "Não recebe url");
});

test("executeShare - AbortError retorna cancelled e não chama fallback", async () => {
  const result = await executeShare("Meu texto", {
    navigatorShare: async () => {
      const error = new Error("AbortError");
      error.name = "AbortError";
      throw error;
    },
    locationAssign: () => {
      throw new Error("Não deve chamar locationAssign");
    },
  });

  assert.equal(result.status, "cancelled");
});

test("executeShare - erro técnico chama fallback", async () => {
  let locationAssigned = false;
  const result = await executeShare("Meu texto", {
    navigatorShare: async () => {
      const error = new Error("TypeError");
      error.name = "TypeError";
      throw error;
    },
    locationAssign: (url) => {
      locationAssigned = url;
    },
  });

  assert.equal(result.status, "redirected");
  assert.equal(locationAssigned, "https://wa.me/?text=Meu%20texto");
});

test("executeShare - fallback (sem navigatorShare) retorna redirected", async () => {
  let locationAssigned = false;
  const result = await executeShare("Texto de teste 100%", {
    navigatorShare: undefined,
    locationAssign: (url) => {
      locationAssigned = url;
    },
  });

  assert.equal(result.status, "redirected");
  assert.equal(locationAssigned, "https://wa.me/?text=Texto%20de%20teste%20100%25");
});
