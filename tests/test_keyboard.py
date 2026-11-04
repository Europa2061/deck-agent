"""验证 Steam 键盘动画焦点恢复和页面可用区。"""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class KeyboardTests(unittest.TestCase):
    def test_animation_focus_and_native_host_bounds(self):
        result = subprocess.run(['node', '-e', r'''
const ts=require('typescript'),fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const compile=p=>ts.transpileModule(fs.readFileSync(p,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const exportsLayout={};vm.runInNewContext(compile('src/components/composer-viewport.ts'),{exports:exportsLayout});
const box=exportsLayout.composerViewport;
// 键盘位置尚未更新时，必须跟随 Steam 已经缩小的页面容器。
assert.deepEqual(JSON.parse(JSON.stringify(box({height:534,topBar:40,footer:48,keyboard:{top:0,bottom:267},host:{top:0,bottom:295},viewport:null}))),{top:40,bottom:287});
assert.equal(box({height:534,topBar:40,footer:48,keyboard:{top:0,bottom:534},host:null,viewport:null}).top,40);
assert.equal(box({height:534,topBar:40,footer:48,keyboard:{top:0,bottom:239},host:{top:239,bottom:534},viewport:null}).top,247);
let callbacks,raf=[],focusCalls=0,hideCalls=0;
const doc={body:{},documentElement:{},activeElement:null};
const win={requestAnimationFrame:f=>raf.push(f),dispatchEvent:()=>{},Event:class{}};doc.defaultView=win;
const el={ownerDocument:doc,isConnected:true,disabled:false,focus(){doc.activeElement=el;focusCalls++}};
const manager={m_currentVirtualKeyboardRef:null,m_bIsInlineVirtualKeyboardOpen:{Value:false},CreateVirtualKeyboardRef(opts){callbacks=opts;const ref={SetAsCurrentVirtualKeyboardTarget(){manager.m_currentVirtualKeyboardRef=ref},ShowVirtualKeyboard(){manager.m_bIsInlineVirtualKeyboardOpen.Value=true;opts.onKeyboardShow();doc.activeElement=doc.body},DelayHideVirtualKeyboard(){hideCalls++}};return ref}};
const Router={WindowStore:{SteamUIWindows:[{m_BrowserWindow:win,m_VirtualKeyboardManager:manager}]}};
const exportsKeyboard={};vm.runInNewContext(compile('src/steam-keyboard.ts'),{exports:exportsKeyboard,require:()=>({Router}),WeakMap,WeakSet});
exportsKeyboard.openKeyboard(el);assert.equal(doc.activeElement,doc.body);
raf.splice(0).forEach(f=>f());assert.equal(doc.activeElement,el);
doc.activeElement=doc.body;callbacks.onKeyboardFullyVisible();assert.equal(doc.activeElement,el);
const other={};doc.activeElement=other;callbacks.onKeyboardFullyVisible();assert.equal(doc.activeElement,other);
exportsKeyboard.hideKeyboard(el);doc.activeElement=doc.body;callbacks.onKeyboardFullyVisible();assert.equal(doc.activeElement,doc.body);assert.equal(hideCalls,1);
console.log('keyboard regression checks passed');
'''], cwd=ROOT, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
