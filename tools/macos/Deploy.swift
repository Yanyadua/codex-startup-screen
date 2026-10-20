import Foundation
import AppKit
import CryptoKit

struct Deployment: Decodable {
    let target: String
    let staged: String
    let backup: String
    let archivedInstalledOriginal: String
    let workspace: String
    let status: String
    let originalAsarHash: String
    let stagedAsarHash: String
}
let fm = FileManager.default
let args = CommandLine.arguments
if args.count < 3 { fputs("Usage: codex-startup-deploy check|apply|restore config.json [--delay seconds]\n", stderr); exit(64) }
let mode = args[1]
let cfg: Deployment
 do { cfg = try JSONDecoder().decode(Deployment.self, from: Data(contentsOf: URL(fileURLWithPath: args[2]))) }
 catch { fputs("Invalid deployment configuration: \(error)\n", stderr); exit(65) }
var movedOriginal: String? = nil
var placedReplacement = false
func status(_ phase: String, _ message: String, extra: [String: Any] = [:]) {
    var value: [String:Any] = ["phase":phase,"message":message,"operation":mode,"updatedAt":ISO8601DateFormatter().string(from:Date()),"target":cfg.target]
    for (k,v) in extra { value[k]=v }
    do {
        let data = try JSONSerialization.data(withJSONObject:value,options:[.prettyPrinted,.sortedKeys])
        try data.write(to:URL(fileURLWithPath:cfg.status),options:.atomic)
    } catch { fputs("Cannot write status: \(error)\n",stderr) }
    print("\(phase): \(message)"); fflush(stdout)
}
func failure(_ text: String) -> NSError { NSError(domain:"CodexStartupDeployment",code:1,userInfo:[NSLocalizedDescriptionKey:text]) }
func run(_ executable: String, _ arguments: [String]) throws {
    let task=Process(); task.executableURL=URL(fileURLWithPath:executable);task.arguments=arguments
    task.standardOutput=FileHandle.standardOutput;task.standardError=FileHandle.standardError
    try task.run(); task.waitUntilExit()
    if task.terminationStatus != 0 { throw failure("\(executable) failed with exit \(task.terminationStatus)") }
}
func hash(_ path:String) throws -> String {
    let handle=try FileHandle(forReadingFrom:URL(fileURLWithPath:path));defer{try? handle.close()}
    var digest=SHA256()
    while let part=try handle.read(upToCount:4*1024*1024), !part.isEmpty { digest.update(data:part) }
    return digest.finalize().map{String(format:"%02x",$0)}.joined()
}
func validateApp(_ path:String) throws {
    try run("/usr/bin/codesign",["--verify","--deep","--strict",path])
    guard let info=NSDictionary(contentsOfFile:path+"/Contents/Info.plist"),info["CFBundleIdentifier"] as? String == "com.openai.codex" else { throw failure("Unexpected application identity") }
}
func installedInstances() -> [NSRunningApplication] {
    NSRunningApplication.runningApplications(withBundleIdentifier:"com.openai.codex").filter {
        $0.executableURL?.standardizedFileURL.path == cfg.target+"/Contents/MacOS/ChatGPT"
    }
}
func pump(_ interval:TimeInterval) { RunLoop.current.run(until:Date().addingTimeInterval(interval)) }
func quitInstalledApp() throws {
    let running=installedInstances()
    status("requesting_quit","正在让正式版正常退出并保存状态",extra:["pids":running.map{Int($0.processIdentifier)}])
    for application in running {
        if !application.terminate() && !application.isTerminated { throw failure("The application declined a normal quit request; nothing was replaced") }
    }
    let limit=Date().addingTimeInterval(90)
    while !installedInstances().isEmpty && Date()<limit { pump(0.25) }
    if !installedInstances().isEmpty { throw failure("The application is still running; replacement cancelled without force quitting") }
    pump(1.5)
}
func launchAndCheck() throws -> Int32 {
    status("launching","已替换程序，正在重新打开")
    let options=NSWorkspace.OpenConfiguration();options.activates=true;options.createsNewApplicationInstance=true
    var complete=false; var launched:NSRunningApplication?; var launchError:Error?
    NSWorkspace.shared.openApplication(at:URL(fileURLWithPath:cfg.target),configuration:options){app,error in
        launched=app;launchError=error;complete=true
    }
    let limit=Date().addingTimeInterval(45)
    while !complete && Date()<limit { pump(0.25) }
    if let error=launchError { throw error }
    guard let application=launched else { throw failure("No launched application was returned") }
    let healthLimit=Date().addingTimeInterval(15)
    while Date()<healthLimit {
        if application.isTerminated { throw failure("The modified application exited during startup") }
        pump(0.5)
    }
    return application.processIdentifier
}
func restoreAfterFailure() {
    guard let previous=movedOriginal else { return }
    do {
        // Never move a replacement out from under a live process.
        for app in installedInstances(){ _=app.terminate() }
        let end=Date().addingTimeInterval(30)
        while !installedInstances().isEmpty && Date()<end {pump(0.25)}
        guard installedInstances().isEmpty else {status("rollback_waiting_for_quit","替换版仍在运行，原版备份保留；请退出后运行恢复工具");return}
        if placedReplacement && fm.fileExists(atPath:cfg.target){
            let failed=cfg.workspace+"/failed-replacement-"+UUID().uuidString+".app"
            try fm.moveItem(atPath:cfg.target,toPath:failed)
        }
        if !fm.fileExists(atPath:cfg.target){try fm.moveItem(atPath:previous,toPath:cfg.target)}
        try validateApp(cfg.target)
        NSWorkspace.shared.openApplication(at:URL(fileURLWithPath:cfg.target),configuration:NSWorkspace.OpenConfiguration()){_,_ in}
        pump(2)
        status("rolled_back","启动或验证失败，已恢复替换前的原程序")
    } catch {status("rollback_failed","恢复需要人工处理：\(error.localizedDescription)",extra:["preservedOriginal":previous])}
}

do {
    guard cfg.target == "/Applications/ChatGPT.app" else {throw failure("This installer is scoped only to /Applications/ChatGPT.app")}
    guard fm.isWritableFile(atPath:"/Applications") else {throw failure("当前用户不能写入 /Applications，尚未替换程序")}
    try validateApp(cfg.backup)
    if mode == "check" {
        try validateApp(cfg.staged)
        guard try hash(cfg.staged+"/Contents/Resources/app.asar")==cfg.stagedAsarHash else{throw failure("Staged application hash mismatch")}
        guard try hash(cfg.target+"/Contents/Resources/app.asar")==cfg.originalAsarHash else{throw failure("Installed version changed; rebuild the patch")}
        print("CHECK PASSED: staged build, signed original backup, target version and write access")
        exit(0)
    }
    guard mode == "apply" || mode == "restore" else {throw failure("Unknown mode")}
    var replacement=cfg.staged
    if mode == "apply" {
        try validateApp(replacement)
        guard try hash(replacement+"/Contents/Resources/app.asar")==cfg.stagedAsarHash else{throw failure("Staged application changed")}
        guard try hash(cfg.target+"/Contents/Resources/app.asar")==cfg.originalAsarHash else{throw failure("Installed version changed; nothing was replaced")}
    } else {
        guard try hash(cfg.target+"/Contents/Resources/app.asar")==cfg.stagedAsarHash else {throw failure("Installed application changed; refusing to overwrite an update during restore")}
        replacement=cfg.workspace+"/restore-ready-"+UUID().uuidString+".app"
        try run("/usr/bin/ditto",[cfg.backup,replacement]);try validateApp(replacement)
    }
    var delay:Double=0
    if let index=args.firstIndex(of:"--delay"),index+1<args.count{delay=Double(args[index+1]) ?? 0}
    status("scheduled",delay>0 ? "补丁已就绪，将在 \(Int(delay)) 秒后退出、替换并重新打开正式版" : "补丁已就绪，开始退出和替换",extra:["delaySeconds":delay,"backup":cfg.backup])
    let start=Date().addingTimeInterval(max(0,delay))
    while Date()<start{
        if fm.fileExists(atPath:cfg.workspace+"/cancel") {status("cancelled","安装已取消，正式版没有改变");exit(0)}
        pump(0.25)
    }
    try quitInstalledApp()
    // Recheck immediately before the swap, in case the updater changed the bundle.
    if mode == "apply" {
        if try hash(cfg.target+"/Contents/Resources/app.asar") != cfg.originalAsarHash {throw failure("The installed application was updated; replacement cancelled")}
    }
    let previous=mode == "apply" ? cfg.archivedInstalledOriginal : cfg.workspace+"/restored-modified-"+UUID().uuidString+".app"
    guard !fm.fileExists(atPath:previous) else{throw failure("The preservation path already exists")}
    status("replacing","正式版已退出，正在原位替换程序；账号和聊天数据目录不作改动")
    try fm.moveItem(atPath:cfg.target,toPath:previous);movedOriginal=previous
    try fm.moveItem(atPath:replacement,toPath:cfg.target);placedReplacement=true
    try validateApp(cfg.target)
    let pid=try launchAndCheck()
    status(mode == "apply" ? "installed_and_running" : "restored_and_running",mode == "apply" ? "正式版启动动画补丁已安装，程序已重新打开；登录和完整功能仍需实际确认" : "已恢复原版并重新打开",extra:["pid":Int(pid),"preservedPreviousApp":previous,"fullFunctionalityVerified":false])
} catch {
    status("failed",error.localizedDescription)
    restoreAfterFailure()
    exit(1)
}
