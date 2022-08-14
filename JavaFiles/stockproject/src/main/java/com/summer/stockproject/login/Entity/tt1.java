package com.summer.stockproject.login.Entity;

import javax.persistence.*;
import java.util.List;

@Entity
@Table(name = "tt1")
public class tt1 {

    @Id
    @Column(name = "user")
    private String user;

    @Column(name = "num")
    private int num;

    @OneToMany(mappedBy = "username", cascade= {CascadeType.PERSIST, CascadeType.MERGE, CascadeType.DETACH, CascadeType.REFRESH})
    private List<tt2> hobbies;

    public tt1() {

    }

    public tt1(String user, int num, List<tt2> hobbies) {
        this.user = user;
        this.num = num;
        this.hobbies = hobbies;
    }

    public String getUser() {
        return user;
    }

    public void setUser(String user) {
        this.user = user;
    }

    public int getNum() {
        return num;
    }

    public void setNum(int num) {
        this.num = num;
    }

    public List<tt2> getHobbies() {
        return hobbies;
    }

    public void setHobbies(List<tt2> hobbies) {
        this.hobbies = hobbies;
    }

    @Override
    public String toString() {
        return "tt1{" +
                "user='" + user + '\'' +
                ", num=" + num +
                ", hobbies=" + hobbies +
                '}';
    }
}
