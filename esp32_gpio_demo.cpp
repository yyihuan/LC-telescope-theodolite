#include <Arduino.h>
// 定义LED管脚
#define LED 2


void setup() {
  Serial.begin(115200);  // 初始化串口通信，波特率为9600
  Serial.println("Hello, XianLin"); // 向串口发送消息
  pinMode(LED, OUTPUT);  // 将LED的针脚设置为输出模式
}
 
void loop() {
  if (Serial.available() > 0) {  // 如果串口有数据可读
    char incomingByte = Serial.read();  // 读取数据
    Serial.print("Received message: ");  // 在串口上打印接收到的消息
    Serial.println(incomingByte);
    // 如果收到"1"则开灯, 收到0则关灯
    if (incomingByte == 49) {     // // "1"的ASCII码是49
      Serial.println("开灯");
      digitalWrite(LED, HIGH);  // 则点亮LED。
    } else if (incomingByte == 48) { // "0"的ASCII码是48
      Serial.println("关灯");
      digitalWrite(LED, LOW); // 否则熄灭LED。
    }
  }
}