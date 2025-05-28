#include <Arduino.h>

// 继电器控制引脚
#define AZ_CW_PIN 1   // 方位角顺时针(IO1)
#define AZ_CCW_PIN 2  // 方位角逆时针(IO2)
#define ALT_UP_PIN 3  // 高度角升高(IO3)
#define ALT_DOWN_PIN 4 // 高度角降低(IO4)

struct ControlState {
  bool az_cw;
  bool az_ccw;
  bool alt_up;
  bool alt_down;
};

void setup() {
  Serial.begin(115200);
  Serial.println("Relay Control Initialized");
  
  pinMode(AZ_CW_PIN, OUTPUT);
  pinMode(AZ_CCW_PIN, OUTPUT);
  pinMode(ALT_UP_PIN, OUTPUT);
  pinMode(ALT_DOWN_PIN, OUTPUT);
  
  // 初始状态: 复位
  digitalWrite(AZ_CW_PIN, HIGH);
  digitalWrite(AZ_CCW_PIN, HIGH);
  digitalWrite(ALT_UP_PIN, HIGH);
  digitalWrite(ALT_DOWN_PIN, HIGH);

  // 发送复位命令
  Serial.println("Resetting...");
  delay(5000);  // 等待1秒以确保复位完成

  digitalWrite(AZ_CW_PIN, LOW); 
  digitalWrite(AZ_CCW_PIN, LOW);
  digitalWrite(ALT_UP_PIN, LOW);
  digitalWrite(ALT_DOWN_PIN, LOW);

  Serial.println("Reset complete.");
  
}

ControlState parseCommand(const String& command) {
  ControlState state = {HIGH, HIGH, HIGH, HIGH};
  
  // 解析方位角控制部分 (AZ开头)
  int azIndex = command.indexOf("AZ");
  if (azIndex != -1) {
    char azCmd = command.charAt(azIndex + 2);
    if (azCmd == '1') {      // 顺时针
      state.az_cw = LOW;
      state.az_ccw = HIGH;
    } else if (azCmd == '2') { // 逆时针
      state.az_cw = HIGH;
      state.az_ccw = LOW;
    } else if (azCmd == '0') { // 停止
      state.az_cw = LOW;
      state.az_ccw = LOW;
    }
  }

  // 解析高度角控制部分 (EL开头)
  int elIndex = command.indexOf("EL");
  if (elIndex != -1) {
    char elCmd = command.charAt(elIndex + 2);
    if (elCmd == '1') {      // 升高
      state.alt_up = HIGH;
      state.alt_down = LOW;
    } else if (elCmd == '2') { // 降低
      state.alt_up = LOW;
      state.alt_down = HIGH;
    } else if (elCmd == '0') { // 停止
      state.alt_up = LOW;
      state.alt_down = LOW;
    }
  }
  
  return state;
}

void executeControl(const ControlState& state) {
  digitalWrite(AZ_CW_PIN, state.az_cw);
  digitalWrite(AZ_CCW_PIN, state.az_ccw);
  digitalWrite(ALT_UP_PIN, state.alt_up);
  digitalWrite(ALT_DOWN_PIN, state.alt_down);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    Serial.print("Received command: ");
    Serial.println(command);

    // 解析命令
    ControlState state = parseCommand(command);
    
    // 执行控制
    executeControl(state);
  }
  delay(10);
}