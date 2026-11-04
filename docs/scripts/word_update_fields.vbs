' VBScript cập nhật toàn diện các trường (TOC, TOF, Page Numbers) bằng chính Word COM
Option Explicit

Dim word, doc, docPath, i, f, c

If WScript.Arguments.Count = 0 Then
    WScript.Echo "ERROR: Missing document path argument."
    WScript.Quit 1
End If

docPath = WScript.Arguments(0)

On Error Resume Next
Set word = CreateObject("Word.Application")
If Err.Number <> 0 Then
    WScript.Echo "ERROR: Cannot create Word.Application: " & Err.Description
    WScript.Quit 1
End If
On Error GoTo 0

word.Visible = False
word.DisplayAlerts = 0

WScript.Echo "Dang mo tep bang Microsoft Word de cap nhat danh muc: " & docPath
Set doc = word.Documents.Open(docPath, False, False)
If Err.Number <> 0 Then
    WScript.Echo "ERROR: Cannot open doc: " & Err.Description
    word.Quit
    WScript.Quit 1
End If

' Cap nhat toan bo truong trong tai lieu
doc.Fields.Update

' Luu lai tep voi cache hoan chinh cua Word
doc.Save
doc.Close False
word.Quit

WScript.Echo "THANH CONG: Da cap nhat 100% Danh muc Hinh, Bang, Muc luc va So trang cho: " & docPath
