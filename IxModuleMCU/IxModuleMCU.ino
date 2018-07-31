/*
 * Daxsonics IxModule MCU
 * IxModule Trigger Generaton, Pulse Voltate, & TGC Control
 * Author: J. Leadbetter, 2014
 * Daxsonics Inc.
*/

//#include "avr/pgmspace.h"
#include <SPI.h>
#include <Wire.h>


//Clear bit macro
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
//Set bit macro
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))

#define SUCCESS 1
#define FAIL    0

//operation codes
#define TRIGGER_MANUAL         0
#define PPULSE                 3
#define NPULSE                 4
#define HILO                   5
#define TGC_START              7
#define TGC_SLOPE              8
#define ECHO                   9

//Pin definitions
#define TRIGGER_IN       2   //Timing sync trigger
#define TRIGGER_OUT      3   //Output trigger for IxModule
#define GAIN_HILO        9



//SPI chip select macros
#define TRIGGER_OUT_HIGH digitalWrite(TRIGGER_OUT, HIGH)
#define TRIGGER_OUT_LOW  digitalWrite(TRIGGER_OUT, LOW)
#define GAIN_HIGH digitalWrite(GAIN_HILO, HIGH)
#define GAIN_LOW  digitalWrite(GAIN_HILO, LOW)



//DEFAULT PARAMETERS
const float refclk=16.0E+06 / (255.0);

//PRF for continuous tirggering
//Trigger count for burst mode
float PRF  = 1500.0;
float TRIG_STOP_CNT = 250;

//Pulse voltage DAC default values (0.0 to 1.0)
unsigned int V_POS   = 255;
unsigned int V_NEG   = 255;

//TGC control default values
unsigned int V_TGC_START = 128;
unsigned int V_TGC_SLOPE = 127;


// Variables used inside interrupt service declared as voilatile
volatile unsigned long  icnt;              // var inside interrupt
volatile unsigned long  phaccu = 0;        // pahse accumulator
volatile unsigned long  tWord;             // dds tuning word m
volatile unsigned long  phaseRef;          // phase offset integer
volatile unsigned short newVal = 0;        // Registers true when new DAC value is avail
volatile unsigned short TRIGGER_OUT_STATE = 0;
volatile unsigned short TRANSFER_STATE = 0;
volatile unsigned short HILO_STATE = 0;

void setup()
{
  //Pin configuration
  pinMode(TRIGGER_IN, INPUT);   //Trigger input
  pinMode(TRIGGER_OUT, OUTPUT); //Trigger output
  pinMode(GAIN_HILO, OUTPUT);      //Chip select for Ch. 1 reference voltage DAC
  
  TRIGGER_OUT_LOW;
  if (HILO_STATE == 1){
    GAIN_HIGH;
  }else{
    GAIN_LOW;
  }
  
  //Setup serial communication port to recieve instructions from user
  //Serial.begin(9600);
  Serial.begin(115200); 
  
  
  Wire.begin();
    
  // High voltage regulators
  
  Wire.beginTransmission(B0010010); // GND address for slave address map
  Wire.write(B00110000); // write to the input register of DAC A and update All (control/address)
  Wire.write(V_POS); // write to full rail position (value byte)
  Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
  Wire.endTransmission(); // stop transmitting
  
   
  Wire.beginTransmission(B0010010); // GND address for slave address map
  Wire.write(B00110001); // write to the input register of DAC B and update All (control/address)
  Wire.write(V_NEG); // write to full rail position (value byte)
  Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
  Wire.endTransmission(); // stop transmitting
 
  //Gain min
  Wire.beginTransmission(B0010000); // GND address for slave address map
  Wire.write(B00110000); // write to the input register of DAC A and update All (control/address)
  Wire.write(V_TGC_START); // write to half rail position (value byte)
  Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
  Wire.endTransmission(); // stop transmitting
  
  //Gain Slope
  Wire.beginTransmission(B0010000); // GND address for slave address map
  Wire.write(B00110001); // write to the input register of DAC B and update All (control/address)
  Wire.write(V_TGC_SLOPE); // write to half rail position (value byte)
  Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
  Wire.endTransmission(); // stop transmitting
  
  
  /*
  //Setup DDS and timer
  phaseRef=pow(2,32)*PHASE/360;       // calulate DDS phase offset
  tWord=pow(2,32)*DFREQ/refclk;       // calulate DDS new tuning word 
  setupDDStimer();
    
  // Set external interrupt 0 (pin2) as a phase reset trigger
  // Direct ADR method - produces faster interrupts
  Setup_INT0();
  
  //Enable delay
  sbi (TIMSK0,TOIE0);
  
  //Pull the Ch. 1 latch high to ensure CH1 DAC's initial values are synced
  digitalWrite(LATCH, HIGH);
  
  //Set an initial value to the scanner DAC
  writeMCP492x(DCcode, DAC_CONFIG, DAC_CS);
  writeMCP492x(DCcode, DAC_CONFIG, REF_CS);
  //Pull the Ch. 1 latch low to enable updates
  digitalWrite(LATCH, LOW);
  
  delay(100);

  //Disable delay
  cbi (TIMSK0,TOIE0);
  */
}


void loop()
{  
  // Check for new instructions on the serial port
  if (Serial.available() > 0){
    readSerial();
  }
}

 
//******************************************************************
// I2C write function for DAC used as pulse voltage and TGC ramp control
void writeLTC2633(uint16_t data, uint8_t config, uint8_t csPin) {
  return;

}
  

//******************************************************************
// Timer setup
void setupDDStimer() {

  //disable timer2 while settings are applied
  cbi (TIMSK2,TOIE2);
  
  // Timer2 Clock Prescaler to 1 (counts at clock rate)
  sbi (TCCR2B, CS20);
  cbi (TCCR2B, CS21);
  cbi (TCCR2B, CS22);
  
  // Mode 0: Normal operation (no PWM)
  TCNT2 = 0;
  cbi (TCCR2A, WGM20);  
  cbi (TCCR2A, WGM21);
  cbi (TCCR2B, WGM22);

  // Set the behaviour of the compare register output pin
  // For timer2, compare register A, this is OC2A.
  // On the Arduino Uno OC2A is mapped to pin 11. 
  // Pin 11 is needed for SPI communication, so OC2A must be disabled
  cbi (TCCR2A, COM2A0); 
  cbi (TCCR2A, COM2A1);
  
  // Enable Timer2 overflow interrupt
  sbi (TIMSK2,TOIE2);  
  // Disable Timer0 to reduce jitter, this makes delay() unavailable
  cbi (TIMSK0,TOIE0);
               
}


//******************************************************************
// Timer2 Interrupt Service
// this is the timebase REFCLOCK for the DDS generator
// FOUT = (M (REFCLK)) / (2 exp 32)
ISR(TIMER2_OVF_vect) {

  //Pin 7 to observe timing
  //sbi(PORTD,7);          // Test / set PORTD,7 high to observe timing with a oscope

  phaccu = phaccu+tWord;   // Increment 32 bit DDS phase accu
  icnt = phaccu >> 24;     // Take upper 12 bits from phase accu to use with amplitude lookup
  newVal = 1;              // Let loop() know there is a new value to output
  
  //***NOTES***//
  //1) The SPI write function runs countinusiously in the main program loop.
  //   DAC output will be updated with the new phase accumulator on the next write call.
  //2) SPI library functions should not be called form here as they use the the SPI 
  //   interrupt register, leading to nested interrupt.
  //3) SPI data streaming is takes time, having excess code inside the ISR
  //   may cause an phase reset interrupt (trigger) to be missed. 

  //Pin 7 to observe timing
  //cbi(PORTD,7);            // reset PORTD,7
}


//******************************************************************
// Setup_int0()
// enable external interrupt and set it to activate on a rising trigger 
void Setup_INT0()  {
    sbi (EIMSK, INT0);  //Enable INT0
    sbi (EICRA, ISC00); //Trigger on rising edge of INT0
    sbi (EICRA, ISC01); //Trigger on rising edge of INT0
}


//******************************************************************
// ISR(INT0_vect)
// Set the DDS phase accumulator to the desired initial angle
// This is the direct AVR method that will trigger from interrupt pin 0
ISR(INT0_vect) { 
  TCNT2 = 0;
  phaccu = phaseRef;
}

void readSerial() {
  
  int i;
  uint16_t  dataCode = 0;
  uint8_t   echoCode = 0;
  float     dataVal  = 0.0;
  
  //Some serial instruction has been recieved.
  
  //First byte is always the operation code
  byte opCode  = Serial.read();
    
  switch (opCode) {
    
    //Resume AC scaning from DC output
    case TRIGGER_MANUAL:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      TRIGGER_OUT_HIGH;
      delayMicroseconds(25);
      TRIGGER_OUT_LOW;
      delayMicroseconds(500);
      
      //Send a command to host to indicate trigger complete
      
      byte dummy;
      while(Serial.available() > 0){
        //Serial.println("Dummy bytes loop");
        dummy = Serial.read();
  }      
       Serial.println(1);
//      while (Serial.available() == 2){
//        dataCode = serialReadUShort(); //dataCode is currently unused here, just clearing the buffer...
//      }
//      else{
//        Serial.println("Serial Data Error: Trigger command expecting unsigned short (2 bytes).");
//      }

      break;


    //Adjust positive pulse voltage amplitude
    case PPULSE:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      // do some error check for correct number of bytes
      if (Serial.available() == 2){
        dataCode = serialReadUShort();

          // asign new amplitude scale
          V_POS = dataCode;
          
          Wire.beginTransmission(B0010010); // GND address for slave address map
          Wire.write(B00110000); // write to the input register of DAC A and update All (control/address)
          Wire.write(V_POS); // write to full rail position (value byte)
          Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
          Wire.endTransmission(); // stop transmitting
          
          Serial.println(V_POS);
      }
      else {
        Serial.println("Serial Data Error: AMP_ADJUST expecting ushort (2 bytes).");
      }
      break;
      
    //Adjust positive pulse voltage amplitude
    case NPULSE:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      // do some error check for correct number of bytes
      if (Serial.available() == 2){
        dataCode = serialReadUShort();

        // asign new amplitude scale
        V_NEG = dataCode;
          
        Wire.beginTransmission(B0010010); // GND address for slave address map
        Wire.write(B00110001); // write to the input register of DAC B and update All (control/address)
        Wire.write(V_NEG); // write to full rail position (value byte)
        Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
        Wire.endTransmission(); // stop transmitting
        
        Serial.println(V_NEG);
      }
      else {
        Serial.println("Serial Data Error: AMP_ADJUST expecting ushort (2 bytes).");
      }
      break;
      
    case HILO:
      
      //Delay to ensure full data stream is recieved.
      serialWait();

      // do some error check for correct number of bytes
      if (Serial.available() == 2){
        dataCode = serialReadUShort();
    
      //Toggle the post amp
      switch (dataCode) {
        case 2:
          if (HILO_STATE == 0){
            GAIN_HIGH;
            HILO_STATE = 1;
          }
          else{
          GAIN_LOW;
          HILO_STATE = 0;
          }
        break;
        
      case 0:
        GAIN_LOW;
        HILO_STATE = 0;      
        break;
        
      case 1:
        GAIN_HIGH;
        HILO_STATE = 1;
        break;
      } 
      Serial.println(HILO_STATE);  
      }
      else{
        Serial.println("Serial Data Error: HiLo Command expecting unsigned short (2 bytes).");
      }    
      break;

    //Adjust minum gain
    case TGC_START:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      // do some error check for correct number of bytes
      if (Serial.available() == 2){
        dataCode = serialReadUShort();

          // asign new start scale
          V_TGC_START = dataCode;
          
          Wire.beginTransmission(B0010000); // GND address for slave address map
          Wire.write(B00110001); // write to the input register of DAC A and update All (control/address)
          Wire.write(V_TGC_START); // write to half rail position (value byte)
          Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
          Wire.endTransmission(); // stop transmitting
          
          Serial.println(V_TGC_START);
      }
      else {
        Serial.println("Serial Data Error: AMP_ADJUST expecting ushort (2 bytes).");
      }
      break;
      
    //Adjust positive pulse voltage amplitude
    case TGC_SLOPE:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      // do some error check for correct number of bytes
      if (Serial.available() == 2){
        dataCode = serialReadUShort();

        // asign new amplitude scale
        V_TGC_SLOPE = dataCode;
          
        Wire.beginTransmission(B0010000); // GND address for slave address map
        Wire.write(B00110000); // write to the input register of DAC B and update All (control/address)
        Wire.write(V_TGC_SLOPE); // write to half rail position (value byte)
        Wire.write(B00000000); // write dummy signals for final byte in protocol (value byte)
        Wire.endTransmission(); // stop transmitting
        
        Serial.println(V_TGC_SLOPE);
      }
      else {
        Serial.println("Serial Data Error: AMP_ADJUST expecting ushort (2 bytes).");
      }
      break;    

    //Echo recieved serial data to verify connection
    case ECHO:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      if (Serial.available() == 2){
        dataCode = serialReadUShort();
        Serial.print(dataCode);
      }
      else{
        dataCode = 0;
        Serial.println("Serial Data Error: ECHO expecting unsigned short (2 bytes).");
      }   
      break;
      
    //Invalid operation code!!
    default:
      
      //Delay to ensure full data stream is recieved.
      serialWait();
      
      Serial.println("Serial Data Error: Invalid operation code.");
    break;
  }
  
  //Clear unsused bytes from the buffer
  //This should only occur from transmission errors
  byte dummy;
  while(Serial.available() > 0){
    Serial.println("Dummy bytes loop");
    dummy = Serial.read();
  }

}

void serialWait() {
  sbi (TIMSK0,TOIE0);
  delay(1);
  cbi (TIMSK0,TOIE0);
}

unsigned short serialReadUShort() {
  union u_tag {
    byte b[2];
    unsigned short ulval;
  } u;
  u.b[0] = Serial.read();
  u.b[1] = Serial.read();
  return u.ulval;
}

double serialReadFloat() {
  union u_tag {
    byte b[4];
    float dval;
  } u;
  u.b[0] = Serial.read();
  u.b[1] = Serial.read();
  u.b[2] = Serial.read();
  u.b[3] = Serial.read();
  return u.dval;
}


