unit dlgPyIDEBase;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs;

type
  TPyIDEDlgBase = class(TForm)
    procedure FormCreate(Sender: TObject);
  private
    { Private declarations }
  public
    { Public declarations }
  end;

var
  PyIDEDlgBase: TPyIDEDlgBase;

implementation

uses
  uCommonFunctions,
  JvGnugettext;

{$R *.dfm}

procedure TPyIDEDlgBase.FormCreate(Sender: TObject);
begin
  TranslateComponent(Self);
  Font.PixelsPerInch := FCurrentPPI;
  SetDefaultUIFont(Font);
  {$IF CompilerVersion >= 36}
  Font.IsDPIRelated := True;
  {$ELSE}
  Font.PixelsPerInch := Screen.PixelsPerInch;
  {$ENDIF}
end;

end.
